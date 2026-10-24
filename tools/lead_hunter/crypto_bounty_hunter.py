#!/usr/bin/env python3
"""
Crypto Bounty Hunter - Focus on Web3 / smart-contract / crypto project bounties.
Searches GitHub for high-signal crypto bounties across Solidity, Rust, DeFi, bridges.
Includes manual high-value targets (Immunefi, Cantina, Sherlock, Code4rena, Firedancer).
"""
import os, sys, re, subprocess, requests
from datetime import datetime, timezone
from typing import List, Dict

GITHUB_API = "https://api.github.com/search/issues"

def gh_headers():
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CryptoBountyHunter/1.0",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    tok = os.getenv("GITHUB_TOKEN")
    if not tok:
        try:
            tok = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except Exception:
            tok = None
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h

# Valid GitHub search queries (no illegal nested parentheses)
CRYPTO_QUERIES = [
    'label:bounty is:issue is:open solidity',
    'label:bounty is:issue is:open "smart contract"',
    'label:bounty is:issue is:open defi',
    'label:bounty is:issue is:open solana',
    'label:bounty is:issue is:open "bridge" web3',
    'label:"💎 Bounty" is:issue is:open crypto',
]

NOISE_REPO = re.compile(r"bounty|scout|watcher|plaza|hunter|earn|airdrop|tracker|radar", re.I)

def days_old(iso_date: str) -> float:
    created = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - created).total_seconds() / 86400

def search_github(query: str, max_results: int = 15) -> List[Dict]:
    params = {
        "q": query,
        "sort": "created",
        "order": "desc",
        "per_page": min(max_results, 50),
    }
    try:
        resp = requests.get(GITHUB_API, headers=gh_headers(), params=params, timeout=30)
        if resp.status_code in (403, 429):
            wait = int(resp.headers.get("Retry-After", 30))
            print(f"  [rate limited] sleeping {wait}s...", file=sys.stderr)
            import time
            time.sleep(wait)
            resp = requests.get(GITHUB_API, headers=gh_headers(), params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"GitHub search failed for '{query}': {e}", file=sys.stderr)
        return []

    results = []
    for item in items:
        repo = "/".join(item["repository_url"].split("/")[-2:])
        if NOISE_REPO.search(repo):
            continue
        age = days_old(item["created_at"])
        comments = item.get("comments", 0)
        results.append({
            "title": item["title"][:90],
            "url": item["html_url"],
            "repo": repo,
            "labels": [l["name"] for l in item.get("labels", [])][:5],
            "age_days": round(age, 1),
            "comments": comments,
        })
    return results

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("=== Crypto / Web3 Bounty Issues on GitHub ===\n")
    seen = set()
    all_results = []
    for q in CRYPTO_QUERIES:
        for r in search_github(q):
            if r["url"] not in seen:
                seen.add(r["url"])
                all_results.append(r)

    for b in sorted(all_results, key=lambda x: (x["comments"], x["age_days"]))[:25]:
        clean_title = b['title'].encode('ascii', errors='ignore').decode()
        clean_labels = [l.encode('ascii', errors='ignore').decode() for l in b['labels']]
        print(f"[{b['age_days']:5.1f}d | {b['comments']:2d} cmts] {clean_title}")
        print(f"  {b['repo']}  |  Labels: {', '.join(clean_labels)}")
        print(f"  {b['url']}\n")

    print("\n=== Verified High-Value Web3 Platforms & APIs ===")
    print("• Superteam Earn (Solana Live API): https://earn.superteam.fun  (e.g., Validator ordering $2,500 USDC)")
    print("• Sherlock Contests API: https://audits.sherlock.xyz/api/contests  (Audits & protocol insurance pools)")
    print("• Immunefi: https://immunefi.com/explore/  (LayerZero $15M, Stargate $10M, Sky $10M)")
    print("• Cantina: https://cantina.xyz/  (Uniswap $15.5M)")
    print("• Code4rena: https://code4rena.com/  (Pre-launch audit pools $50k-$500k+)")
    print("• Firedancer (Jump Crypto Alpenglow): Up to $300k boosted reward window through mid-Nov 2026")
    print("\nTips: Always verify live scope + PoC rules. Start mid-tier, deliver clean reproducible exploits.")

if __name__ == "__main__":
    main()
