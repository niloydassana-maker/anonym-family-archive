#!/usr/bin/env python3
"""
Hunter-cum-Dispatcher (High-Speed REST Engine -> GitHub Actions Engine 2)
========================================================================
Combines Grok's high-speed multi-platform REST search (Algora, Opire, BountyHub,
IssueHunt, Open Collective) with strict Zero-Competition and Anti-Phantom gates,
dispatching verified tasks directly to GitHub Actions.
"""
import sys
import os
import re
import time
import json
import sqlite3
import argparse
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Ensure scripts/ is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import autonomous_icu_pipeline as aip
from fleet_recovery_policy import non_engineering_dispatch_reason

ACTIONS_REPO = "isearchxsolve/anonym-family-archive"
DB_FILE = r"D:\anonym\scratch\icu_pipeline.db"
MIN_BOUNTY_USD = Decimal("80.00")
MAX_OPEN_PRS = 2

console = Console(legacy_windows=False)

def get_gh_token():
    t = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT") or os.getenv("GH_TOKEN")
    if t:
        return t
    try:
        import subprocess
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return None

GITHUB_TOKEN = get_gh_token()
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

# Grok's High-Yield Multi-Platform Search Matrix
HUNTER_QUERIES = [
    # 1. Algora High-Ticket & Verified
    ('commenter:algora-pbc is:issue is:open "bounty"', "Algora"),
    ('label:"💎 Bounty" is:issue is:open', "Algora/Label"),
    ('"/bounty $" is:issue is:open', "Algora/Command"),

    # 2. Opire
    ('opire.dev is:issue is:open', "Opire"),
    ('"/reward" is:issue is:open', "Opire"),

    # 3. BountyHub
    ('bountyhub is:issue is:open', "BountyHub"),
    ('bountyhub-bot is:issue is:open', "BountyHub"),

    # 4. IssueHunt
    ('issuehunt.io is:issue is:open', "IssueHunt"),
    ('issuehunt is:issue is:open', "IssueHunt"),

    # 5. Direct / Open Collective
    ('label:bounty "Open Collective" is:issue is:open', "OpenCollective"),
    ('label:bounty "$100" is:issue is:open', "DirectBounty"),
    ('label:bounty "$200" is:issue is:open', "DirectBounty"),
    ('label:bounty "$500" is:issue is:open', "DirectBounty"),
    ('"will pay" "$100" is:issue is:open', "DirectPay"),
    ('label:"💰 Bounty" is:issue is:open', "DirectBounty"),
]

def gh_get(url: str, params: dict = None) -> dict:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 403 and "rate limit" in r.text.lower():
                reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 60))
                sleep = max(5, reset - time.time())
                console.print(f"[yellow]Rate limit reached -> sleeping {sleep:.0f}s[/yellow]")
                time.sleep(sleep)
                continue
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1)
    return {}

def dispatch_task_to_github_actions(repo: str, number: int, title: str, run_id: str = "") -> bool:
    """Dispatches verified task to Engine 2 workflow on GitHub Actions."""
    cmd = [
        "gh", "api", f"repos/{ACTIONS_REPO}/dispatches",
        "-X", "POST",
        "-f", "event_type=bounty_task_dispatch",
        "-f", f"client_payload[repo]={repo}",
        "-F", f"client_payload[issue_number]={number}",
        "-f", f"client_payload[title]={title}",
        "-f", f"client_payload[run_id]={run_id or f'gh-{number}'}",
    ]
    out, err, code = aip.run_cmd(cmd, timeout=30)
    if code == 0:
        console.print(f"🚀 [bold green][DISPATCHED TO GITHUB ACTIONS][/bold green] {repo}#{number} -> {ACTIONS_REPO} (Engine 2)")
        return True
    console.print(f"❌ [red][DISPATCH FAILED][/red] {repo}#{number}: {err or out}")
    return False

def record_dispatch(repo: str, number: int, title: str, db_path=DB_FILE):
    try:
        with closing(sqlite3.connect(db_path, timeout=30)) as con, con:
            con.execute("""
            INSERT INTO deliveries (repo, issue_number, status, reason, delivered_at)
            VALUES (?, ?, 'DISPATCHED_TO_ACTIONS', ?, datetime('now'))
            ON CONFLICT(repo, issue_number) DO UPDATE SET
                status = 'DISPATCHED_TO_ACTIONS',
                reason = excluded.reason,
                delivered_at = datetime('now')
            """, (repo, number, f"Dispatched to GitHub Actions: {title[:100]}"))
            con.commit()
    except Exception as e:
        console.print(f"  [DB Record Dispatch Error] {e}")

def run_hunter_cycle(max_dispatches: int = 2):
    console.print("=" * 70)
    console.print(f"⚡ [bold cyan]HUNTER-CUM-DISPATCHER ACTIVE[/bold cyan] (REST Engine -> GitHub Actions Engine 2)")
    console.print(f"Target Runner: {ACTIONS_REPO} (.github/workflows/engine2.yml)")
    console.print(f"Platforms: Algora • Opire • BountyHub • IssueHunt • OpenCollective")
    console.print(f"Filter Policy: Floor >= ${MIN_BOUNTY_USD}, Zero Competition Pre-Check, Anti-Phantom Moat")
    console.print("=" * 70)

    dispatched_count = 0
    seen_in_run = set()

    for q_idx, (query, platform) in enumerate(HUNTER_QUERIES, 1):
        if dispatched_count >= max_dispatches:
            console.print(f"\n[green][QUOTA REACHED] Dispatched {dispatched_count} tasks in this cycle. Yielding.[/green]")
            break

        console.print(f"\n[{q_idx}/{len(HUNTER_QUERIES)}] Query: {query} ({platform})")
        data = gh_get(
            "https://api.github.com/search/issues",
            {"q": query, "sort": "created", "order": "desc", "per_page": 25},
        )
        items = data.get("items", [])
        console.print(f"  -> Fetched {len(items)} raw issues from wire")

        for it in items:
            if dispatched_count >= max_dispatches:
                break

            repo_url = it.get("repository_url", "")
            number = it.get("number")
            if not repo_url or not number:
                continue

            repo = "/".join(repo_url.rstrip("/").split("/")[-2:])
            repo_lower = repo.lower()
            issue_id = f"{repo}#{number}"

            if issue_id in seen_in_run:
                continue
            seen_in_run.add(issue_id)

            # Skip known spam farms, scrapers, and bot repos
            if any(farm in repo_lower for farm in (
                "scibase-ai", "securebananalabs", "unitoneai", "bujiproject",
                "louis-os", "poyraz", "bounty-plaza", "devpool-directory", "mergeearn",
                "realworldproblems", "test-info", "bounty-bot", "bountyscout"
            )):
                continue

            title = it.get("title", "")
            body = it.get("body", "") or ""
            full_text = f"{title}\n{body}"

            # Anti-phantom filter: reject marketing experiments, ad spend, and speculative proposals
            if re.search(r"\[(?:roadmap|rfc|proposal|design|spec|experiment)\]", title, re.I):
                continue
            if re.search(r"\b(?:ad\s+spend|facebook\s+ad|interview\s+incentive|willingness-to-pay|validation\s+plan)\b", full_text, re.I):
                continue

            # Check database ledger
            claimed, status = aip.is_issue_claimed_or_delivered(repo, number)
            if claimed:
                console.print(f"  [dim][SKIP] {issue_id} already in ledger status: {status}[/dim]")
                continue

            # Check bounty amount
            has_bounty, in_bounds, raw_cur, usd_val, reason = aip.parse_and_normalize_bounty(full_text)
            if not has_bounty:
                # Fast fallback regex for $ / USDC / Tier amounts
                tier_match = re.search(r"(?:bounty|reward|funded)?\s*[\$€]\s?(\d{2,5})", full_text, re.I)
                if tier_match:
                    usd_val = Decimal(tier_match.group(1))
                    has_bounty = True
                elif re.search(r"\bmedium\b", full_text, re.I) and "bounty" in full_text.lower():
                    usd_val = Decimal("150.00")
                    has_bounty = True

            if usd_val is not None and usd_val < MIN_BOUNTY_USD:
                console.print(f"  [dim][BELOW FLOOR] {issue_id}: ${usd_val} < ${MIN_BOUNTY_USD}[/dim]")
                continue

            # Fail-Closed Zero-Competition Check
            is_zero_comp, comp_reason = aip.check_competing_prs_fail_closed(repo, number)
            if not is_zero_comp:
                console.print(f"  [yellow][COMPETING PR / BLOCKED] {issue_id}: {comp_reason}[/yellow]")
                continue

            # Codebase Reality Gate: Ensure repo has recognized programming languages
            repo_view = aip.run_cmd(["gh", "repo", "view", repo, "--json", "isEmpty,languages"], timeout=15)
            if repo_view[2] == 0 and repo_view[0]:
                try:
                    rv_data = json.loads(repo_view[0])
                    if rv_data.get("isEmpty") or not rv_data.get("languages"):
                        console.print(f"  [dim][DUMMY/EMPTY REPO] {issue_id}: No programming languages detected.[/dim]")
                        continue
                except Exception:
                    pass

            # Hardness and Task Validation
            task_dict = {"repo": repo, "title": title, "body": body}
            non_eng = non_engineering_dispatch_reason(task_dict)
            if non_eng:
                console.print(f"  [dim][NON-ENG] {issue_id}: {non_eng}[/dim]")
                continue

            hardness_score = aip.score_hardness_and_competition(task_dict)

            console.print(Panel(
                f"[bold green]QUALIFIED UNCONTESTED BOUNTY IDENTIFIED[/bold green]\n"
                f"Repository:  {repo}#{number}\n"
                f"Title:       {title}\n"
                f"Reward:      ${usd_val or 'Attested'}\n"
                f"Platform:    {platform}\n"
                f"Competition: 0 open PRs (Verified)\n"
                f"Link:        {it.get('html_url')}",
                title=f"🎯 Target Ready for Cloud Dispatch",
                border_style="green"
            ))

            # Dispatch directly to GitHub Actions Engine 2
            success = dispatch_task_to_github_actions(repo, number, title)
            if success:
                record_dispatch(repo, number, title)
                dispatched_count += 1
                time.sleep(2)

        time.sleep(0.8)

    console.print("\n" + "=" * 70)
    console.print(f"Cycle Complete. Total Tasks Dispatched to GitHub Actions: {dispatched_count}")
    console.print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunter-cum-Dispatcher Live Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in a loop")
    parser.add_argument("--interval", type=int, default=180, help="Interval in seconds between cycles (default: 180)")
    parser.add_argument("--max-dispatches", type=int, default=2, help="Max tasks to dispatch per cycle (default: 2)")
    args = parser.parse_args()

    if args.daemon:
        console.print(f"🔄 [bold green]Starting Hunter-cum-Dispatcher in DAEMON mode[/bold green] (Interval: {args.interval}s, Max/Cycle: {args.max_dispatches})...")
        while True:
            try:
                run_hunter_cycle(max_dispatches=args.max_dispatches)
            except Exception as e:
                console.print(f"[red][DAEMON CYCLE ERROR][/red] {e}")
            console.print(f"\n💤 Sleeping {args.interval}s until next hunt cycle...\n")
            time.sleep(args.interval)
    else:
        run_hunter_cycle(max_dispatches=args.max_dispatches)
