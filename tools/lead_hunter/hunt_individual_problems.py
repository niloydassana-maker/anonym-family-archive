#!/usr/bin/env python3
"""
hunt_individual_problems.py - Hunt for INDIVIDUAL users/founders facing hard, impossible engineering problems with direct cash offers.
NO CONTESTS. NO HACKATHONS. NO REGIONAL RESTRICTIONS.
Direct issue-to-PR resolution paid upon merge.
"""
import os, sys, re, time, subprocess, requests, csv
from datetime import datetime, timezone

GH_API = "https://api.github.com/search/issues"
OPIRE_API = "https://api.opire.dev/rewards"

QUERIES = [
    'is:issue is:open "will pay" "$"',
    'is:issue is:open "paying" "$" fix',
    'is:issue is:open "bounty" "$" crash',
    'is:issue is:open "bounty" "$" memory',
    'is:issue is:open "bounty" "$" performance',
    'is:issue is:open "bounty" "$" deadlock',
    'is:issue is:open "bounty" "$" bug',
    'is:issue is:open "reward" "$" bug',
    'is:issue is:open "bounty: $"'
]

NOISE_PATTERNS = re.compile(
    r"contest|hackathon|airdrop|leaderboard|weekly digest|scout|watcher|tracker|radar|earn\.superteam",
    re.I
)

AMOUNT_RE = re.compile(r"(?:US?D\s?|\$\s?)([\d]{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s?(k)?", re.I)

def gh_headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "IndividualProblemHunter/1.0"}
    tok = os.getenv("GITHUB_TOKEN")
    if not tok:
        try:
            tok = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except Exception:
            tok = None
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h

def extract_amount(text):
    if not text:
        return 0
    best = 0
    for m in AMOUNT_RE.finditer(text):
        val = float(m.group(1).replace(",", ""))
        if m.group(2):
            val *= 1000
        if 20 <= val <= 50_000:
            best = max(best, val)
    return best

def hunt_github_individual_issues():
    headers = gh_headers()
    results = {}
    print("[GITHUB] Hunting issues posted by individual users with hard problems & direct payment...", file=sys.stderr)
    
    for q in QUERIES:
        full_query = f"{q} no:assignee -linked:pr archived:false"
        try:
            r = requests.get(
                GH_API,
                headers=headers,
                params={"q": full_query, "sort": "created", "order": "desc", "per_page": 30},
                timeout=25
            )
            if r.status_code in (403, 429):
                wait = int(r.headers.get("Retry-After", 20))
                print(f"  [rate limited] sleeping {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                continue
                
            items = r.json().get("items", [])
            for it in items:
                title = it.get("title", "")
                body = (it.get("body") or "")[:3000]
                url = it.get("html_url", "")
                repo = "/".join(url.split("/")[-4:-2])
                
                # Filter out spam/contests
                if NOISE_PATTERNS.search(title) or NOISE_PATTERNS.search(repo):
                    continue
                
                amt = extract_amount(title) or extract_amount(body)
                if amt < 30:
                    continue
                    
                created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - created).days
                
                results[url] = {
                    "source": "github_direct",
                    "repo": repo,
                    "title": title,
                    "url": url,
                    "amount_usd": amt,
                    "comments": it.get("comments", 0),
                    "age_days": age_days,
                    "user": it.get("user", {}).get("login", "")
                }
            time.sleep(2)
        except Exception as e:
            print(f"  [error] Query '{q}': {e}", file=sys.stderr)
            
    return list(results.values())

def hunt_opire_direct_rewards():
    print("[OPIRE] Checking direct user-funded rewards on GitHub issues...", file=sys.stderr)
    out = []
    try:
        r = requests.get(OPIRE_API, timeout=15)
        if r.status_code == 200:
            data = r.json()
            items = data if isinstance(data, list) else data.get("rewards", data.get("data", []))
            for it in items:
                claimers = len(it.get("claimerUsers", []))
                if claimers > 0:
                    continue
                amt_cents = it.get("pendingPrice", {}).get("value", 0)
                amt_usd = amt_cents / 100.0 if amt_cents else extract_amount(str(it.get("amount", "")))
                if amt_usd < 40:
                    continue
                url = it.get("url", "")
                title = it.get("title", "")
                proj = it.get("project", {}).get("name", "")
                org = it.get("organization", {}).get("name", "")
                repo = f"{org}/{proj}" if org and proj else "github"
                
                created_ms = it.get("createdAt", 0)
                age_days = round((time.time() - (created_ms / 1000.0)) / 86400.0, 1) if created_ms else 0
                
                out.append({
                    "source": "opire_escrow",
                    "repo": repo,
                    "title": title,
                    "url": url,
                    "amount_usd": amt_usd,
                    "comments": len(it.get("tryingUsers", [])),
                    "age_days": age_days,
                    "user": org or "creator"
                })
    except Exception as e:
        print(f"  [error] Opire fetch failed: {e}", file=sys.stderr)
    return out

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        
    all_issues = []
    all_issues += hunt_opire_direct_rewards()
    all_issues += hunt_github_individual_issues()
    
    # Sort by amount descending, then by lowest comments
    all_issues.sort(key=lambda x: (x["amount_usd"], -x["comments"]), reverse=True)
    
    print("\n" + "="*80)
    print(" 🔥 INDIVIDUAL HARD ENGINEERING PROBLEMS WITH DIRECT PAYMENT OFFERS")
    print("    (No Contests, No Hackathons, Direct PR Merges Paid Immediately)")
    print("="*80 + "\n")
    
    for i, it in enumerate(all_issues[:20], 1):
        clean_title = it['title'].encode('ascii', errors='ignore').decode()[:65]
        print(f"[{i:2d}] ${it['amount_usd']:>6,.0f} | {it['source']:13} | cmts: {it['comments']:2d} | age: {it['age_days']:>4}d | {it['repo']}")
        print(f"     Title: {clean_title}")
        print(f"     Link : {it['url']}\n")
        
    # Save CSV
    out_csv = "D:\\anonym\\tools\\lead_hunter\\individual_paid_problems.csv"
    fields = ["source", "amount_usd", "comments", "age_days", "repo", "title", "url", "user"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_issues)
    print(f"Saved {len(all_issues)} candidates to {out_csv}")

if __name__ == "__main__":
    main()
