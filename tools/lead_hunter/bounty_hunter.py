#!/usr/bin/env python3
"""
bounty_hunter.py - find open, unclaimed, PAID technical problems.

Sources:
  1. GitHub issues carrying bounty labels / bounty text (covers Algora, BountyHub,
     project-run bounties like Remotion, Tenstorrent, Cal.com).
  2. Opire public rewards API (https://api.opire.dev/rewards) - verified USD bounties.
  3. Superteam Earn (Solana) open bounties, via verified live API (https://earn.superteam.fun/api/listings).
  4. (opt-in) Stack Exchange featured questions with open bounties (WARNING: reputation points, NOT money).

Filters: open, no assignee, no linked PR, few comments/submissions, verified or parsed USD amount.
Output : ranked table in terminal + bounties.csv + bounties.md

Usage:
  python bounty_hunter.py --include-superteam --debug
  python bounty_hunter.py --min-usd 50 --max-comments 5
  python bounty_hunter.py --include-superteam --max-submissions 10
"""
import argparse, csv, datetime as dt, os, re, sys, time, subprocess
import requests

GH = "https://api.github.com"
SE = "https://api.stackexchange.com/2.3"
OPIRE_API = "https://api.opire.dev/rewards"
ST_HOSTS = ["https://earn.superteam.fun/api/listings", "https://superteam.fun/api/listings"]
USD_TOKENS = {"USDC", "USDT", "USDG", "PYUSD", "USD"}

# Each query is a GitHub issue-search string. Qualifiers are added later.
GH_QUERIES = [
    'label:"💎 Bounty"',          # Algora convention, Remotion, many others
    'label:bounty "$"',
    'label:Bounty',
    '"opire.dev" in:comments',
    '"/bounty" in:comments',        # Algora slash command used in comments
    'repo:tenstorrent/tt-metal is:issue is:open',
    'repo:calcom/cal.com is:issue is:open label:"💎 Bounty"',
    'bounty in:title "$"',
]

AMOUNT_RE = re.compile(r"(?:US?D\s?|\$\s?)([\d]{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s?(k)?", re.I)
USD_WORD_RE = re.compile(r"([\d,]+)\s?(?:USD|dollars)", re.I)


def gh_headers():
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = os.getenv("GITHUB_TOKEN")
    if not tok:
        try:
            tok = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except Exception:
            tok = None
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def parse_amount(*texts):
    """Best-effort USD extraction. Returns the largest plausible figure or 0."""
    best = 0
    for t in texts:
        if not t:
            continue
        for m in AMOUNT_RE.finditer(t):
            v = float(m.group(1).replace(",", ""))
            if m.group(2):
                v *= 1000
            best = max(best, v)
        for m in USD_WORD_RE.finditer(t):
            best = max(best, float(m.group(1).replace(",", "") or 0))
    return best if best <= 1_000_000 else 0


def gh_search(query, pages, sleep):
    out = []
    headers = gh_headers()
    for page in range(1, pages + 1):
        try:
            r = requests.get(
                f"{GH}/search/issues",
                headers=headers,
                params={"q": query, "sort": "created", "order": "desc", "per_page": 50, "page": page},
                timeout=30,
            )
            if r.status_code in (403, 429):
                wait = int(r.headers.get("Retry-After", 30))
                print(f"  [rate limited] sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code == 422:
                print(f"  [skip] GitHub rejected query: {query}", file=sys.stderr)
                break
            r.raise_for_status()
            items = r.json().get("items", [])
            out.extend(items)
            if len(items) < 50:
                break
            time.sleep(sleep)
        except Exception as e:
            print(f"  [error] {e}", file=sys.stderr)
            break
    return out


def hunt_github(args):
    results = {}
    base = "is:issue is:open no:assignee -linked:pr archived:false"
    langs = args.lang if args.lang else [None]

    for q in GH_QUERIES:
        for lang in langs:
            full = f"{q} {base}" + (f" language:{lang}" if lang else "")
            print(f"[github] {full}", file=sys.stderr)
            for it in gh_search(full, args.pages, args.sleep):
                if it["id"] in results:
                    continue
                labels = [l["name"] for l in it.get("labels", [])]
                amt = parse_amount(it["title"], " ".join(labels), (it.get("body") or "")[:4000])
                created = dt.datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
                age = (dt.datetime.now(dt.timezone.utc) - created).days
                results[it["id"]] = {
                    "source": "github",
                    "title": it["title"],
                    "url": it["html_url"],
                    "repo": it["repository_url"].split("repos/")[-1],
                    "amount": amt,
                    "unit": "USD (parsed, verify!)" if amt else "unknown",
                    "comments": it["comments"],
                    "age_days": age,
                    "labels": ",".join(labels),
                }
            time.sleep(args.sleep)
    return list(results.values())


def hunt_opire(args):
    print(f"[opire] fetching {OPIRE_API}", file=sys.stderr)
    out = []
    try:
        r = requests.get(OPIRE_API, timeout=20)
        if r.status_code != 200:
            print(f"  [skip] Opire returned status {r.status_code}", file=sys.stderr)
            return []
        items = r.json()
        if not isinstance(items, list):
            items = items.get("rewards", items.get("data", []))
        for it in items:
            amt_cents = it.get("pendingPrice", {}).get("value", 0)
            amt_usd = amt_cents / 100.0 if amt_cents else parse_amount(str(it.get("amount", "")))
            if amt_usd < args.min_usd:
                continue
            claimers = len(it.get("claimerUsers", []))
            if claimers > 0:
                continue
            trying = len(it.get("tryingUsers", []))
            created_ms = it.get("createdAt", 0)
            age_days = round((time.time() - (created_ms / 1000.0)) / 86400.0, 1) if created_ms else 0
            proj = it.get("project", {}).get("name", "")
            org = it.get("organization", {}).get("name", "")
            repo = f"{org}/{proj}" if org and proj else "github"
            out.append({
                "source": "opire",
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "repo": repo,
                "amount": amt_usd,
                "unit": "USD (verified Opire)",
                "comments": trying,
                "age_days": age_days,
                "labels": ",".join(it.get("programmingLanguages", [])),
            })
    except Exception as e:
        print(f"  [error] Opire fetch failed: {e}", file=sys.stderr)
    return out


def _first(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def hunt_superteam(args):
    """Open Superteam Earn bounties via verified live API."""
    data = None
    for url in ST_HOSTS:
        for params in ({"context": "all", "take": 50}, {"take": 50}, {}):
            try:
                r = requests.get(url, params=params, timeout=30,
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if r.status_code == 200:
                    data = r.json()
                    break
            except (requests.RequestException, ValueError):
                continue
        if data is not None:
            break
    if data is None:
        print("[superteam] no endpoint answered; check the URL manually", file=sys.stderr)
        return []
    items = data if isinstance(data, list) else _first(data, "listings", "data", "items", default=[])
    if args.debug and items:
        print(f"[superteam] sample keys: {sorted(items[0].keys())}", file=sys.stderr)
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for it in items:
        typ = str(_first(it, "type", default="bounty")).lower()
        status = str(_first(it, "status", default="OPEN")).upper()
        if typ not in ("bounty", "project") or status not in ("OPEN", "ACTIVE"):
            continue
        deadline = _first(it, "deadline", "applicationDeadline")
        if deadline:
            try:
                d = dt.datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
                if d < now:
                    continue
            except ValueError:
                pass
        subs = _first(it, "submissionCount", "submissions", "_count", default=0)
        if isinstance(subs, dict):
            subs = _first(subs, "Submission", "submissions", default=0)
        subs = int(subs) if str(subs).isdigit() else 0
        token = str(_first(it, "token", default="")).upper()
        amt = float(_first(it, "rewardAmount", "usdValue", default=0) or 0)
        slug = _first(it, "slug", default="")
        sponsor = _first(_first(it, "sponsor", default={}), "name", default="") if isinstance(_first(it, "sponsor"), dict) else ""
        rows.append({
            "source": "superteam",
            "title": str(_first(it, "title", default="?")),
            "url": f"https://earn.superteam.fun/listing/{slug}" if slug else "https://earn.superteam.fun",
            "repo": sponsor or "superteam",
            "amount": amt,
            "unit": "USD (stablecoin)" if token in USD_TOKENS else f"{token or '?'} (NOT USD, check)",
            "comments": subs,
            "age_days": 0,
            "labels": f"agentAccess={_first(it, 'agentAccess', default='?')}",
        })
    return rows


def hunt_stackexchange(args):
    rows = []
    for site in args.se_sites:
        print(f"[stackexchange] {site}", file=sys.stderr)
        try:
            r = requests.get(
                f"{SE}/questions/featured",
                params={"site": site, "order": "desc", "sort": "activity", "pagesize": 100,
                        "key": os.getenv("SE_KEY", "")},
                timeout=30,
            )
            if r.status_code != 200:
                print(f"  [skip] {site}: HTTP {r.status_code}", file=sys.stderr)
                continue
            for q in r.json().get("items", []):
                if q.get("answer_count", 0) > args.max_comments:
                    continue
                rows.append({
                    "source": f"se:{site}",
                    "title": q["title"],
                    "url": q["link"],
                    "repo": site,
                    "amount": q.get("bounty_amount", 0),
                    "unit": "REPUTATION (not money)",
                    "comments": q.get("answer_count", 0),
                    "age_days": int((time.time() - q["creation_date"]) // 86400),
                    "labels": ",".join(q.get("tags", [])),
                })
            time.sleep(1)
        except Exception:
            pass
    return rows


NOISE_REPO = re.compile(r"bounty|scout|watcher|plaza|hunter|earn|airdrop|tracker", re.I)
NOISE_TITLE = re.compile(
    r"bounty alert|open bounties right now|payout|\[demand\]|bounty proposal|"
    r"new opportunit|weekly digest|leaderboard|paid out|claimed", re.I)


def is_noise(r):
    return bool(NOISE_REPO.search(r["repo"]) or NOISE_TITLE.search(r["title"]))


def score(r):
    # reward per unit of competition; mild bonus for older (= nobody could solve it)
    return (r["amount"] or 1) / (1 + r["comments"]) * (1 + min(r["age_days"], 365) / 365)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-usd", type=float, default=50)
    ap.add_argument("--max-comments", type=int, default=5)
    ap.add_argument("--lang", nargs="*", help="e.g. python rust typescript")
    ap.add_argument("--max-submissions", type=int, default=10,
                    help="Superteam: skip listings that already have more submissions than this")
    ap.add_argument("--max-age-days", type=int, default=540)
    ap.add_argument("--keep-noise", action="store_true")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--sleep", type=float, default=3)
    ap.add_argument("--include-unknown", action="store_true")
    ap.add_argument("--skip-github", action="store_true", help="skip GitHub issue search (fast scan of Opire & Superteam)")
    ap.add_argument("--include-superteam", action="store_true", help="add Superteam Earn (Solana)")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--include-se", action="store_true", help="add Stack Exchange (reputation bounties)")
    ap.add_argument("--se-sites", nargs="*",
                    default=["stackoverflow", "serverfault", "superuser", "unix", "dba"])
    args = ap.parse_args()

    rows = []
    # 1. Opire verified rewards
    rows += hunt_opire(args)

    # 2. Superteam Earn verified live API
    if args.include_superteam:
        st = [r for r in hunt_superteam(args) if r["comments"] <= args.max_submissions]
        rows += st
        print(f"[superteam] {len(st)} open listings with <= {args.max_submissions} submissions", file=sys.stderr)

    # 3. GitHub issue searches
    if not args.skip_github:
        rows += hunt_github(args)

    # Filter
    rows = [r for r in rows
            if r["comments"] <= (args.max_submissions if r["source"] == "superteam" else args.max_comments)
            and r["age_days"] <= args.max_age_days
            and (args.keep_noise or not is_noise(r))
            and (r["amount"] >= args.min_usd or (args.include_unknown and r["amount"] == 0))]

    if args.include_se:
        rows += hunt_stackexchange(args)

    rows.sort(key=score, reverse=True)

    fields = ["source", "amount", "unit", "comments", "age_days", "repo", "title", "url", "labels"]
    with open("bounties.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: r[k] for k in fields} for r in rows)

    with open("bounties.md", "w", encoding="utf-8") as f:
        f.write("# 💎 Active Open-Source & Technical Bounties\n\n")
        f.write(f"**Generated:** {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
        f.write(f"**Found Candidates:** {len(rows)}\n\n")
        f.write("| # | Source | Amount | Cmts/Subs | Age(d) | Repo/Sponsor | Title |\n|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            amt = f"${r['amount']:,.0f}" if "USD" in r["unit"] else f"{r['amount']} rep"
            clean_title = r['title'].replace('|', '-').strip()[:70]
            f.write(f"| {i} | {r['source']} | {amt} | {r['comments']} | {r['age_days']} | {r['repo']} | [{clean_title}]({r['url']}) |\n")

    print(f"\n{len(rows)} candidates -> bounties.csv, bounties.md\n")
    for r in rows[:25]:
        amt_str = f"${r['amount']:,.0f}" if "USD" in r["unit"] else f"{r['amount']} rep"
        clean_title = r['title'].encode('ascii', errors='ignore').decode()[:60]
        print(f"{amt_str:>8} {r['source']:9} | c={r['comments']:2} | {r['age_days']:>4}d | {r['repo'][:28]:28} | {clean_title}")
        print(f"{'':>18} {r['url']}")


if __name__ == "__main__":
    main()
