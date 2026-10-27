#!/usr/bin/env python3
"""
Hunter-cum-Dispatcher (Autonomous Engine 2 Bridge)
=================================================
Integrates Grok's Master Hunter multi-platform queries (BountyHub, Opire, IssueHunt, Direct, Algora Sniper)
with the Autonomous ICU pre-push gates, and dispatches uncontested tasks directly to GitHub Actions.
"""
import sys
import os
import time
import json
import sqlite3
import subprocess
from contextlib import closing
from decimal import Decimal
from pathlib import Path

# Ensure scripts/ is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import autonomous_icu_pipeline as aip
from fleet_recovery_policy import non_engineering_dispatch_reason

ACTIONS_REPO = "isearchxsolve/anonym-family-archive"
DB_FILE = r"D:\anonym\scratch\icu_pipeline.db"
MIN_BOUNTY_USD = Decimal("80.00")

# Grok's Recommended Multi-Platform Search Matrix
HUNTER_QUERIES = [
    # 1. BountyHub (Low-Medium competition, Stripe/PayPal)
    'bountyhub is:issue is:open',
    'bountyhub-bot is:issue is:open',

    # 2. Opire (Medium competition, developer /try, Stripe)
    'opire.dev is:issue is:open',
    '"/reward" is:issue is:open',
    'opire.dev "$100"',
    'opire.dev "$50"',

    # 3. IssueHunt (Low-Medium competition, EU/JP projects)
    'issuehunt.io is:issue is:open',
    'issuehunt is:issue is:open',

    # 4. Direct / High-Quality Project Bounties (Open Collective / Maintainer)
    'label:bounty "Open Collective" is:issue is:open',
    'label:bounty "$100" is:issue is:open',
    'label:bounty "$200" is:issue is:open',
    'label:bounty "$500" is:issue is:open',
    '"will pay" "$100" is:issue is:open',
    '"will pay" "$500" is:issue is:open',

    # 5. Algora Sniper Mode (High ticket $100+, strictly uncontested)
    '--commenter algora-pbc "$100"',
    '--commenter algora-pbc "$250"',
    '--commenter algora-pbc "$500"',
    '--commenter algora-pbc "$1000"',
]

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
        print(f"🚀 [DISPATCHED TO GITHUB ACTIONS] {repo}#{number} -> {ACTIONS_REPO} (Engine 2)", flush=True)
        return True
    print(f"❌ [DISPATCH FAILED] {repo}#{number}: {err or out}", flush=True)
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
        print(f"  [DB Record Dispatch Error] {e}")

def run_hunter_cycle(max_dispatches=3):
    print("=" * 70, flush=True)
    print("⚡ HUNTER-CUM-DISPATCHER ACTIVE (Multi-Platform -> GitHub Actions Engine 2)", flush=True)
    print(f"Target Runner: {ACTIONS_REPO} (.github/workflows/engine2.yml)", flush=True)
    print(f"Platforms: BountyHub • Opire • IssueHunt • Direct/OpenCollective • Algora (Sniper)", flush=True)
    print(f"Filter Policy: Floor >= ${MIN_BOUNTY_USD}, Open PRs <= 2, Zero Competition Pre-Check", flush=True)
    print("=" * 70, flush=True)

    dispatched_count = 0
    seen_in_run = set()

    for q_idx, query in enumerate(HUNTER_QUERIES, 1):
        if dispatched_count >= max_dispatches:
            print(f"\n[QUOTA REACHED] Dispatched {dispatched_count} tasks in this cycle. Yielding.", flush=True)
            break

        print(f"\n[{q_idx}/{len(HUNTER_QUERIES)}] Query: {query}", flush=True)
        try:
            items = aip.search_issues(query, limit=15)
        except Exception as e:
            print(f"  [Query Error] {e}", flush=True)
            continue

        print(f"  -> Retained {len(items)} query-layer candidates", flush=True)

        for it in items:
            if dispatched_count >= max_dispatches:
                break

            repo = it.get("repository", {}).get("nameWithOwner")
            number = it.get("number")
            title = it.get("title", "")
            if not repo or not number:
                continue

            issue_id = f"{repo}#{number}"
            if issue_id in seen_in_run:
                continue
            seen_in_run.add(issue_id)

            # Check database ledger
            claimed, status = aip.is_issue_claimed_or_delivered(repo, number)
            if claimed:
                print(f"  [SKIP] {issue_id} already in ledger status: {status}")
                continue

            # Fetch fresh issue details
            up = aip.get_issue_fast(repo, number)
            if not up or up.get("state") != "OPEN":
                print(f"  [SKIP] {issue_id} is closed or unreachable.")
                continue

            body = up.get("body", "") or ""
            author_comments = up.get("author_comments", [])
            labels = up.get("labels", [])
            author = (up.get("author") or {}).get("login", "")

            # Hardness & Dispatch Reason check
            task_dict = {"repo": repo, "title": title, "body": body}
            non_eng = non_engineering_dispatch_reason(task_dict)
            if non_eng:
                print(f"  [NON-ENG] {issue_id}: {non_eng}")
                continue

            # Check bounty amount
            total_text = f"{title} {body} " + " ".join(author_comments)
            has_bounty, in_bounds, raw_cur, usd_val, reason = aip.parse_and_normalize_bounty(total_text)
            if usd_val is not None and usd_val < MIN_BOUNTY_USD:
                print(f"  [BELOW FLOOR] {issue_id}: ${usd_val} < ${MIN_BOUNTY_USD}")
                continue

            # Zero-Competition Pre-Push Check (Fail-closed)
            is_zero_comp, comp_reason = aip.check_competing_prs_fail_closed(repo, number)
            if not is_zero_comp:
                print(f"  [COMPETING PR / BLOCKED] {issue_id}: {comp_reason}")
                continue

            # Genuine ICU patient check
            is_icu, icu_reason = aip.verify_genuine_icu_patient(
                title, body, author_comments, labels, repo,
                author_assoc=up.get("authorAssociation", "NONE"),
                author=author,
                payer_assoc=up.get("payerAssociation", "NONE"),
                live_delivery_mode=True
            )
            if not is_icu:
                print(f"  [ICU GATE REJECT] {issue_id}: {icu_reason}")
                continue

            # Hardness Score
            hardness_score = aip.score_hardness_and_competition(task_dict)
            print(f"\n🎯 [QUALIFIED UNCONTESTED BOUNTY FOUND] {issue_id}")
            print(f"   Title:    {title}")
            print(f"   Value:    ${usd_val if usd_val else 'Attested'}")
            print(f"   Hardness: {hardness_score}")
            print(f"   Reason:   {icu_reason}")

            # Dispatch directly to GitHub Actions Engine 2
            success = dispatch_task_to_github_actions(repo, number, title)
            if success:
                record_dispatch(repo, number, title)
                dispatched_count += 1
                time.sleep(2)

    print("\n" + "=" * 70, flush=True)
    print(f"Cycle Complete. Total Tasks Dispatched to GitHub Actions: {dispatched_count}", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    run_hunter_cycle(max_dispatches=2)
