#!/usr/bin/env python3
"""
hunt_crypto_hard_problems.py (v2)

TARGET: individual users (not organisations) who post a hard crypto / Web3 engineering problem on
GitHub and offer to pay for a fix. Org-owned repos and maintainer/org-member bounties are dropped by
default (use --include-org to see them). Contests and hackathons are never searched.

Ranks by EVIDENCE that the payer is real (escrow, account age, owner of the repo), not by the biggest
dollar figure in the text.

What this script does NOT do:
  - It does not measure difficulty. "Hard" is your judgement after reading the issue.
  - It does not verify that anyone will pay. The `payout_verified` column is blank on purpose:
    ask the maintainer in the issue (or their Discord) before you build anything.

SAFETY: reproducing bugs means running code from strangers. Use a throwaway VM with no keys,
wallets or logged-in sessions on it.

Usage:
  export GITHUB_TOKEN=...        # or have `gh auth login` done; never hard-code a token
  python hunt_crypto_hard_problems.py                 # writes ./crypto_hard_problems.csv
  python hunt_crypto_hard_problems.py --max-age 30 --per-repo 1
  python hunt_crypto_hard_problems.py --self-test     # offline checks of the parsing/filter logic
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests

GH_SEARCH = "https://api.github.com/search/issues"
GH_REPO = "https://api.github.com/repos/{}"
OPIRE_API = "https://api.opire.dev/rewards"
# UNVERIFIED assumptions about Opire's response shape. Run with --debug and check one raw item.
OPIRE_AMOUNT_IN_CENTS = True

MIN_USD, MAX_USD = 25, 50_000
FLOOD_THRESHOLD = 5          # a repo appearing this many times in one run is demoted, not dropped
HEADERS = {}

# ----------------------------------------------------------------------------- queries
# GitHub allows at most 5 boolean operators per query, so keep each OR group small.
INDIVIDUAL_BASES = ['"will pay"', '"willing to pay"', '"i will pay"', "bounty"]
ORG_BASES = ['label:"💎 Bounty"', "label:bounty"]   # only with --include-org
# One query PER term. Do NOT use `(a OR b)` groups: on GitHub issue search an OR widens the whole
# query ('"will pay" (solana OR ethereum)' matched 15,684 issues vs 109 for '"will pay" solana',
# and only 1 of 30 results mentioned either word).
CRYPTO_TERMS = ["solana", "ethereum", "solidity", "web3", "blockchain", '"smart contract"', "evm"]

# ----------------------------------------------------------------------------- amount parsing
NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"
# `(?![A-Za-z])` after the optional k stops "$50 key" being read as $50k.
FIAT_RE = re.compile(r"(?:\$|\bUSD\s?)\s?" + NUM + r"\s?(k)?(?![A-Za-z])", re.I)
STABLE_RE = re.compile(NUM + r"\s?(k)?\s?(USDC|USDT|DAI|PYUSD)\b", re.I)
CRYPTO_AMT_RE = re.compile(NUM + r"\s?(SOL|ETH|BTC)\b")
PAY_STRONG = re.compile(r"bount(?:y|ies)|reward|prize|will pay|i['’]ll pay|paying|pay out|payout of", re.I)
LOSS = re.compile(r"\b(lost|stolen|drained|exploit(?:ed)?|hack(?:ed)?|tvl|market ?cap|volume|losses|loss)\b", re.I)


def _val(g1, g2, k):
    v = float(g1.replace(",", "") + ("." + g2 if g2 else ""))
    return v * 1000 if k else v


def _paid(text, m):
    """A dollar figure only counts if a payment word sits next to it (and it isn't a loss/TVL figure)."""
    near = text[max(0, m.start() - 25): m.end() + 25]
    if PAY_STRONG.search(near):
        return True
    far = text[max(0, m.start() - 60): m.end() + 60]
    wide = text[max(0, m.start() - 40): m.end() + 40]
    return bool(PAY_STRONG.search(far)) and not LOSS.search(wide)


def extract_payment(text):
    """Return (amount_usd, token_note). Token amounts (SOL/ETH/BTC) are noted, not converted."""
    best, note = 0.0, ""
    if not text:
        return best, note
    for m in FIAT_RE.finditer(text):
        v = _val(m.group(1), m.group(2), m.group(3))
        if MIN_USD <= v <= MAX_USD and _paid(text, m):
            best = max(best, v)
    for m in STABLE_RE.finditer(text):
        v = _val(m.group(1), m.group(2), m.group(3))
        if MIN_USD <= v <= MAX_USD and _paid(text, m):
            best = max(best, v)
    for m in CRYPTO_AMT_RE.finditer(text):
        if _paid(text, m) and not note:
            note = f"{m.group(1)}{'.' + m.group(2) if m.group(2) else ''} {m.group(3)}"
    return best, note


# ----------------------------------------------------------------------------- relevance
CRYPTO_STRONG = re.compile(
    r"\b(solana|jito|firedancer|agave|anchor[- ]lang|ethereum|evm|solidity|vyper|bitcoin|lightning network|"
    r"blockchain|smart[- ]contracts?|defi|web3|zk-?snarks?|zero[- ]knowledge|rollup|cosmwasm|cosmos sdk|"
    r"substrate|polkadot|secp256k1|ed25519|erc-?20|spl[- ]token)\b", re.I)
CRYPTO_WEAK = re.compile(r"\b(rpc|validator|wallet|consensus|mempool|dex|amm|bridge|staking|token)\b", re.I)


def crypto_relevant(text):
    if CRYPTO_STRONG.search(text):
        return True
    return len({w.lower() for w in CRYPTO_WEAK.findall(text)}) >= 3


# ----------------------------------------------------------------------------- display signals
URGENT_RE = re.compile(r"\b(urgent(?:ly)?|asap|immediately|blocked|blocking|production|stuck|deadline)\b", re.I)
HARD_RE = re.compile(
    r"\b(race condition|deadlock|memory leak|non-?determinis\w*|heisenbug|segfault|panic(?:s|ked)?|"
    r"compute budget|account lock|consensus|desync|reorg|front-?run\w*|mev|zk|prover|invariant)\b", re.I)


def signals(text):
    s = []
    if URGENT_RE.search(text):
        s.append("urgent")
    hard = sorted({m.lower() for m in HARD_RE.findall(text)})
    if hard:
        s.append("hard-words:" + ",".join(hard)[:40])
    return s


# ----------------------------------------------------------------------------- farm detection
STABLES = {"USDC", "USDT", "DAI", "USD", "PYUSD"}
MAJORS = STABLES | {"SOL", "ETH", "BTC", "WBTC", "WETH", "BNB", "MATIC", "OP", "ARB"}
SHELL_VARS = {"PATH", "HOME", "USER", "PWD", "SHELL", "GOPATH", "CARGO", "RUSTFLAGS", "HOSTNAME", "TERM", "LANG", "DISPLAY"}
NOISE_RE = re.compile(
    r"contest|hackathon|airdrop|leaderboard|digest|\bscout\b|watcher|tracker|radar|earn-ops|earn\.superteam|"
    r"gitcoin|quest\b", re.I)
FARM_REPO_RE = re.compile(r"awesome-.*bount|bounty-(plaza|board|hunters?)|agent-bount|bug-bounty-hub", re.I)
FARM_TITLE_RE = re.compile(r"agent[- ]ready|^\W*payment\s*:|^\[[\w.-]+/[\w.-]+\]|\[bounty\]\s*\[bounty\]", re.I)
TICKER_RE = re.compile(r"\$([A-Z][A-Z0-9_]{2,})\b")


def farm_flags(repo, title, body):
    flags = []
    if FARM_REPO_RE.search(repo):
        flags.append("farm-repo-name")
    if FARM_TITLE_RE.search(title):
        flags.append("farm-title")
    if NOISE_RE.search(title) or NOISE_RE.search(repo):
        flags.append("noise")
    text = f"{title} {body[:1500]}"
    odd = set()
    for m in TICKER_RE.finditer(text):
        t = m.group(1)
        if t in MAJORS or t in SHELL_VARS:
            continue
        if PAY_STRONG.search(text[max(0, m.start() - 40): m.end() + 40]):
            odd.add(t)
    if odd:
        flags.append("own-token:" + ",".join(sorted(odd))[:30])
    return flags


def funding_evidence(labels, assoc, source):
    """Evidence, not proof. A label or maintainer post can still be an empty promise."""
    if source == "opire":
        return "opire-escrow"
    if any("💎" in l or "algora" in l.lower() for l in labels):
        return "algora-label"
    if assoc in ("MEMBER", "COLLABORATOR"):
        return "org-member-posted"
    if assoc == "OWNER":
        return "owner-own-repo"
    return "individual-claim"


FUND_W = {"opire-escrow": 3, "algora-label": 3, "owner-own-repo": 1, "individual-claim": 0, "org-member-posted": 0}


# ----------------------------------------------------------------------------- HTTP
def log(*a):
    print(*a, file=sys.stderr)


def gh_headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "CryptoProblemHunter/2.0"}
    tok = os.getenv("GITHUB_TOKEN")
    if not tok:
        try:
            tok = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            tok = None
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def gh_get(url, params=None, tries=3):
    for _ in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=25)
        except requests.RequestException as e:
            log(f"  [network] {e}")
            time.sleep(5)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429):
            wait = r.headers.get("Retry-After")
            if wait is None and r.headers.get("X-RateLimit-Remaining") == "0":
                wait = int(r.headers.get("X-RateLimit-Reset", "0")) - int(time.time()) + 1
            wait = int(wait or 30)
            if wait > 120:
                log(f"  [rate limit] exhausted, resets in {wait}s. Stopping this request (add a token).")
                return None
            log(f"  [rate limit] sleeping {wait}s")
            time.sleep(max(wait, 1))
            continue
        msg = ""
        try:
            msg = r.json().get("message", "")
        except Exception:
            pass
        log(f"  [http {r.status_code}] {msg[:120]}")
        return None
    return None


def days_since(iso):
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days


# ----------------------------------------------------------------------------- GitHub hunt
def hunt_github(max_age, include_org=False, debug=False):
    since = (datetime.now(timezone.utc) - timedelta(days=max_age)).strftime("%Y-%m-%d")
    delay = 2.5 if "Authorization" in HEADERS else 7
    raw = {}
    for base in INDIVIDUAL_BASES + (ORG_BASES if include_org else []):
        for term in CRYPTO_TERMS:
            q = f"is:issue is:open {base} {term} no:assignee -linked:pr archived:false updated:>={since}"
            data = gh_get(GH_SEARCH, {"q": q, "sort": "updated", "order": "desc", "per_page": 30})
            if debug:
                log(f"  q={q}\n    -> {None if data is None else len(data.get('items', []))} items")
            time.sleep(delay)
            if not data:
                continue
            for it in data.get("items", []):
                if "pull_request" in it:
                    continue
                url = it["html_url"]
                raw[url] = it
    log(f"[GITHUB] {len(raw)} unique issues from search")

    repo_hits = Counter(it["repository_url"].split("repos/")[-1] for it in raw.values())
    out = []
    for url, it in raw.items():
        repo = it["repository_url"].split("repos/")[-1]
        title = it.get("title", "")
        body = (it.get("body") or "")[:4000]
        labels = [l["name"] for l in it.get("labels", [])]
        flags = farm_flags(repo, title, body)
        if flags:
            continue  # farm signals are dropped, not demoted
        assoc = it.get("author_association", "")
        if not include_org and assoc in ("MEMBER", "COLLABORATOR"):
            continue  # posted by an org member / maintainer team: org bounty, not an individual
        if not crypto_relevant(f"{title} {repo} {' '.join(labels)} {body[:1500]}"):
            continue
        amt, note = extract_payment(f"{title}\n{body}")
        if amt < MIN_USD and not note:
            continue
        fl = []
        if repo_hits[repo] >= FLOOD_THRESHOLD:
            fl.append(f"repo-flood:{repo_hits[repo]}")
        out.append({
            "source": "github", "repo": repo, "title": title, "url": url, "amount_usd": amt,
            "pay_note": note, "comments": it.get("comments", 0),
            "age_days": days_since(it["created_at"]), "updated_days": days_since(it["updated_at"]),
            "funding": funding_evidence(labels, assoc, "github"),
            "author": (it.get("user") or {}).get("login", ""),
            "signals": signals(f"{title}\n{body}"),
            "flags": fl,
        })
    return out


# ----------------------------------------------------------------------------- Opire hunt
def dig(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
        if d is None:
            return default
    return d


def hunt_opire(debug=False):
    log("[OPIRE] fetching (response shape is UNVERIFIED; use --debug to inspect)")
    out = []
    try:
        r = requests.get(OPIRE_API, timeout=15)
        if r.status_code != 200:
            log(f"  [opire http {r.status_code}]")
            return out
        data = r.json()
    except Exception as e:
        log(f"  [opire error] {e}")
        return out
    items = data if isinstance(data, list) else (data.get("rewards") or data.get("data") or []) if isinstance(data, dict) else []
    if debug and items and isinstance(items[0], dict):
        log("  opire sample keys:", sorted(items[0].keys()))
    passed = 0
    for it in items:
        if not isinstance(it, dict) or it.get("claimerUsers"):
            continue
        raw_amt = dig(it, "pendingPrice", "value")
        amt = (raw_amt / 100.0 if OPIRE_AMOUNT_IN_CENTS else float(raw_amt)) if isinstance(raw_amt, (int, float)) else 0
        if amt < MIN_USD:
            continue
        title = it.get("title", "")
        org, proj = dig(it, "organization", "name", default=""), dig(it, "project", "name", default="")
        langs = " ".join(it.get("programmingLanguages", []) or [])
        if not crypto_relevant(f"{title} {langs} {proj} {org}"):
            continue
        created = it.get("createdAt", 0)
        age = round((time.time() - created / 1000.0) / 86400.0, 1) if created else 0
        out.append({
            "source": "opire", "repo": f"{org}/{proj}" if org and proj else "github", "title": title,
            "url": it.get("url", ""), "amount_usd": amt, "pay_note": "",
            "comments": len(it.get("tryingUsers", []) or []), "age_days": age, "updated_days": age,
            "funding": "opire-escrow", "author": org, "signals": signals(title), "flags": [],
        })
        passed += 1
    log(f"[OPIRE] {len(items)} fetched, {passed} passed filters")
    return out


# ----------------------------------------------------------------------------- ranking
def enrich_user(row):
    u = gh_get(f"https://api.github.com/users/{row['author']}") if row.get("author") else None
    if not u:
        row["user_age_days"] = "?"
        return
    row["user_age_days"] = days_since(u["created_at"])
    if row["user_age_days"] < 90:
        row["flags"].append("new-account")


def enrich_repo(row):
    meta = gh_get(GH_REPO.format(row["repo"])) if "/" in row["repo"] else None
    if not meta:
        row["stars"], row["repo_pushed_days"], row["owner_type"] = "?", "?", "?"
        row["flags"].append("owner-unknown")
        return
    row["owner_type"] = (meta.get("owner") or {}).get("type", "?")
    if row["owner_type"] == "Organization":
        row["flags"].append("org-repo")
    row["stars"] = meta.get("stargazers_count", "?")
    pushed = meta.get("pushed_at")
    row["repo_pushed_days"] = days_since(pushed) if pushed else "?"
    if isinstance(row["repo_pushed_days"], int) and row["repo_pushed_days"] > 60:
        row["flags"].append("repo-inactive")


def score(row):
    s = FUND_W[row["funding"]]
    s += 1 if row["updated_days"] <= 14 else 0
    s += 1 if row["comments"] <= 3 else 0
    s -= 2 if any(f.startswith("repo-flood") for f in row["flags"]) else 0
    s -= 2 if "repo-inactive" in row["flags"] else 0
    s -= 3 if "new-account" in row["flags"] else 0
    s += 1 if "urgent" in row.get("signals", []) else 0
    return s


def cap_per_repo(rows, n):
    seen, out = Counter(), []
    for r in rows:
        if seen[r["repo"]] < n:
            out.append(r)
            seen[r["repo"]] += 1
    return out


# ----------------------------------------------------------------------------- self-test
def self_test():
    cases = [
        ("Bounty $50 key rotation bug", 50), ("bounty $30 kicks off", 30),
        ("Lost $12,000 in exploit, fix pls", 0), ("need fix, TVL $48,000 at risk", 0),
        ("$5.5k bounty", 5500), ("Reward: 100 USDC for fix", 100), ("bounty $1,250 for a fix", 1250),
        ("[$15750.15 USD] bounty", 15750.15),
    ]
    for text, want in cases:
        got, _ = extract_payment(text)
        assert abs(got - want) < 1e-6, (text, got, want)
    assert extract_payment("bounty 0.5 SOL")[1] == "0.5 SOL"
    assert not crypto_relevant("reference sentence experience frustrating")
    assert not crypto_relevant("token validator tool")
    assert farm_flags("airdropia/earn-ops", "superteam digest", "")
    assert farm_flags("a/b", "weekly hackathon contest", "")
    assert crypto_relevant("solana program panics")
    assert crypto_relevant("rpc validator mempool desync")
    assert farm_flags("awesome-agent-bounties", "x", "")
    assert farm_flags("a/b", "[Bounty] [BOUNTY] thing", "")
    assert farm_flags("a/b", "t", "Bounty: 50,000 $ROBIN_MCP")
    assert not farm_flags("a/b", "t", "bounty $50, run `echo $PATH`")
    assert farm_flags("a/b", "[tenstorrent/tt-metal] Bounty", "")
    assert funding_evidence([], "NONE", "github") == "individual-claim"
    assert funding_evidence([], "MEMBER", "github") == "org-member-posted"
    assert funding_evidence(["💎 Bounty"], "NONE", "github") == "algora-label"
    assert "urgent" in signals("blocked in production, will pay")
    assert any(x.startswith("hard-words") for x in signals("random deadlock in consensus"))
    print("self-test OK")


# ----------------------------------------------------------------------------- main
def main():
    global HEADERS
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age", type=int, default=60, help="only issues updated within N days")
    ap.add_argument("--per-repo", type=int, default=2)
    ap.add_argument("--out", default="crypto_hard_problems.csv")
    ap.add_argument("--no-opire", action="store_true")
    ap.add_argument("--include-org", action="store_true", help="also show org-owned repos / org bounties")
    ap.add_argument("--enrich", type=int, default=30, help="repo+account lookups for the top N (uses API quota)")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    HEADERS = gh_headers()
    if "Authorization" not in HEADERS:
        log("[warn] no GitHub token: search is limited to 10 req/min and repo checks to 60/hour")

    rows = [] if a.no_opire else hunt_opire(a.debug)
    rows += hunt_github(a.max_age, a.include_org, a.debug)
    for r in rows:
        r["score"] = score(r)
    rows.sort(key=lambda r: (r["score"], r["amount_usd"]), reverse=True)
    rows = cap_per_repo(rows, a.per_repo)

    for r in rows[:a.enrich]:                # spend lookups only on the top candidates
        if r["source"] == "github":
            enrich_repo(r)
            enrich_user(r)
    for r in rows[a.enrich:]:
        r["flags"].append("unchecked-owner")
    if not a.include_org:
        rows = [r for r in rows if "org-repo" not in r["flags"]]
    for r in rows:
        r["score"] = score(r)
    rows.sort(key=lambda r: (r["score"], r["amount_usd"]), reverse=True)

    print("\n" + "=" * 88)
    print(" CANDIDATES, ranked by payer-evidence + freshness (NOT by dollar size)")
    print(" 'funding' is evidence, not proof. Confirm payout with the maintainer before building.")
    print("=" * 88 + "\n")
    for i, r in enumerate(rows[:20], 1):
        amt = f"${r['amount_usd']:,.0f}" if r["amount_usd"] else (r["pay_note"] or "?")
        print(f"[{i:2d}] score {r['score']:>2} | {amt:>9} | {r['funding']:17} | cmts {r['comments']:>2} | "
              f"upd {r['updated_days']}d | {r['repo']}  {' '.join(r['flags'])}")
        if r.get("signals"):
            print(f"     signals: {' '.join(r['signals'])}")
        print(f"     {r['title'].encode('ascii', 'ignore').decode()[:80]}")
        print(f"     {r['url']}\n")

    fields = ["score", "funding", "amount_usd", "pay_note", "comments", "age_days", "updated_days",
              "author", "user_age_days", "owner_type", "stars", "repo_pushed_days", "signals", "source",
              "repo", "title", "url", "flags", "payout_verified"]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r = dict(r, flags=";".join(r["flags"]), signals=";".join(r.get("signals", [])), payout_verified="")
            w.writerow(r)
    print(f"Saved {len(rows)} candidates to {a.out}  (payout_verified is blank on purpose)")


if __name__ == "__main__":
    main()
