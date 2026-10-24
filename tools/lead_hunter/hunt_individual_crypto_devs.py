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
    "User-Agent": "IndividualCryptoHunter/1.0"
}

# Target individual developer queries
QUERIES = [
    'is:issue is:open "will pay" solana updated:>=2026-08-01',
    'is:issue is:open "willing to pay" solana updated:>=2026-08-01',
    'is:issue is:open "will pay" "smart contract" updated:>=2026-08-01',
    'is:issue is:open "willing to pay" "smart contract" updated:>=2026-08-01',
    'is:issue is:open "bounty" solana no:assignee updated:>=2026-09-01',
    'is:issue is:open "bounty" "trading bot" no:assignee updated:>=2026-08-01',
    'is:issue is:open "will pay" "trading bot" updated:>=2026-08-01',
    'is:issue is:open "will pay" solidity updated:>=2026-08-01',
    'is:issue is:open "bounty" "solidity" no:assignee updated:>=2026-09-01',
    'is:issue is:open "bounty" jito no:assignee updated:>=2026-08-01',
    'is:issue is:open "will pay" rpc crypto updated:>=2026-08-01'
]

NOISE_REPOS = re.compile(
    r"bounty-plaza|devpool|airdrop|earn-ops|superteam|quest|radar|bounty-bot|awesome-|microcredit-agent",
    re.I
)

PAY_RE = re.compile(r"(\$?\d+[\d,]*\s*(?:USD|USDC|USDT|SOL|ETH|dollars|\$))|will pay|willing to pay|bounty", re.I)

seen_urls = set()
candidates = []

print("Starting hunt for INDIVIDUAL crypto developers with hard engineering problems...", flush=True)

for q in QUERIES:
    print(f"\n[Query] {q}", flush=True)
    try:
        r = requests.get(
            "https://api.github.com/search/issues",
            headers=headers,
            params={"q": q, "sort": "updated", "order": "desc", "per_page": 20},
            timeout=15
        )
    except Exception as e:
        print(f"  [error] {e}", flush=True)
        time.sleep(4)
        continue

    if r.status_code != 200:
        print(f"  [status {r.status_code}] {r.text[:100]}", flush=True)
        time.sleep(5)
        continue

    items = r.json().get("items", [])
    print(f"  -> {len(items)} items found", flush=True)

    for it in items:
        url = it.get("html_url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        repo = it.get("repository_url", "").split("repos/")[-1]
        if NOISE_REPOS.search(repo):
            continue

        title = it.get("title", "")
        body = it.get("body") or ""
        comments = it.get("comments", 0)
        user = (it.get("user") or {}).get("login", "")
        user_type = (it.get("user") or {}).get("type", "")

        # Skip bots
        if "[bot]" in user or user_type == "Bot":
            continue

        # Check repository owner type (individual vs org)
        owner = repo.split("/")[0]
        # Skip known bot orgs
        if owner.lower() in ("ubiquity", "devpool-directory", "superteam", "gitcoin"):
            continue

        text = f"{title}\n{body}"

        # Match payment intent
        pay_match = PAY_RE.search(text)
        if not pay_match:
            continue

        candidates.append({
            "repo": repo,
            "title": title,
            "url": url,
            "author": user,
            "comments": comments,
            "updated": it.get("updated_at", "")[:10],
            "body_snippet": body[:400].replace("\n", " ")
        })

    time.sleep(4)  # Respect rate limit and prevent 403

print(f"\n=======================================================", flush=True)
print(f"FOUND {len(candidates)} INDIVIDUAL CRYPTO PROBLEMS", flush=True)
print(f"=======================================================\n", flush=True)

for i, c in enumerate(candidates, 1):
    print(f"[{i:2d}] {c['repo']} by @{c['author']} (updated: {c['updated']}, cmts: {c['comments']})", flush=True)
    print(f"     Title: {c['title']}", flush=True)
    print(f"     URL: {c['url']}", flush=True)
    print(f"     Snippet: {c['body_snippet'][:200]}...", flush=True)
    print("", flush=True)
