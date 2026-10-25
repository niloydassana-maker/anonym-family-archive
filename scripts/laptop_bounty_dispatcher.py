import os
import sys
import re
import time
import json
import sqlite3
import urllib.request
import subprocess
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Tuple, Optional

# Enforce UTF-8 line buffering
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DOOR = "https://omniroute-relay.omniroute-fleet-kd.workers.dev"
DOOR_TOKEN = "GOLD24"
CLIENT_CONTACT_EMAIL = "isearch.xsolve@gmail.com"
SETTLEMENT_WALLET = "0x3a5E08708dd1CF22AAe94f913Ab69b17b80a3dC5"

BASE_DIR = r"D:\anonym"
SCRATCH_DIR = os.path.join(BASE_DIR, "scratch")
ICU_DB = os.path.join(SCRATCH_DIR, "icu_pipeline.db")
VAULT_DIR = os.path.join(BASE_DIR, "vault")

def get_gh_token() -> str:
    token_path = os.path.join(VAULT_DIR, "gh_token.txt")
    if os.path.exists(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def init_db():
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    with sqlite3.connect(ICU_DB, timeout=30) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                claimed_at TEXT,
                delivered_at TEXT,
                pr_url TEXT,
                reason TEXT,
                UNIQUE(repo, issue_number)
            )
        """)
        con.commit()

def is_issue_claimed_or_delivered(repo: str, issue_number: int) -> Tuple[bool, str]:
    try:
        with sqlite3.connect(ICU_DB, timeout=10) as con:
            cur = con.cursor()
            row = cur.execute(
                "SELECT status FROM deliveries WHERE repo = ? AND issue_number = ?",
                (repo, issue_number)
            ).fetchone()
            if row:
                return True, row[0]
            return False, ""
    except Exception:
        return False, ""

def record_dispatch(repo: str, issue_number: int, task_id: str, reason: str = ""):
    with sqlite3.connect(ICU_DB, timeout=30) as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO deliveries (repo, issue_number, status, claimed_at, reason)
            VALUES (?, ?, 'DISPATCHED_TO_KAGGLE', datetime('now'), ?)
            ON CONFLICT(repo, issue_number) DO UPDATE SET
                status = 'DISPATCHED_TO_KAGGLE',
                claimed_at = datetime('now'),
                reason = excluded.reason
        """, (repo, issue_number, reason))
        con.commit()

# Tracker / Honeypot / Discussion repos to strictly reject
EXCLUDED_REPO_PATTERNS = [
    r"-tracker\b", r"-bounties\b", r"bounty-plaza", r"algo-bounty",
    r"\.github\.io\b", r"space-station-14", r"agente-bountie", r"zec-bounties"
]

def is_genuine_code_issue(repo: str, title: str, body: str) -> Tuple[bool, str]:
    # 1. Reject known non-code / tracker repos
    for pat in EXCLUDED_REPO_PATTERNS:
        if re.search(pat, repo, re.IGNORECASE):
            return False, f"Non-code tracker or honeypot repo: {repo}"

    # 2. Reject spam/discussion titles
    combined = (title + " " + body).lower()
    if any(k in combined for k in ["[scam]", "bounty spam", "no cost to create", "discussion only", "rfp only"]):
        return False, "Discussion, spam, or non-actionable issue"

    # 3. Require minimum length
    if len(body.strip()) < 40:
        return False, "Issue description too short"

    return True, ""
    """
    Enforces Rule 5: The Zero-Competition Law.
    Checks whether an unmerged open PR touches or references this issue.
    """
    try:
        res = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--state", "open", "--json", "number,title,body,headRefName"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20
        )
        if res.returncode != 0:
            return False, ""
        prs = json.loads(res.stdout)
        issue_pattern = f"#{issue_number}"
        for p in prs:
            p_text = f"{p.get('title', '')} {p.get('body', '')} {p.get('headRefName', '')}"
            if issue_pattern in p_text or f"fixes #{issue_number}" in p_text.lower() or f"closes #{issue_number}" in p_text.lower():
                return True, f"Competing open PR exists: #{p.get('number')} - {p.get('title')}"
        return False, ""
    except Exception as e:
        return False, ""

def dispatch_task_to_kaggle(task_payload: dict) -> bool:
    try:
        data = json.dumps({"body": "BOUNTY_TASK", "text": json.dumps(task_payload)}).encode("utf-8")
        req = urllib.request.Request(
            f"{DOOR}/say?token={DOOR_TOKEN}",
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "laptop-bounty-dispatcher"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Dispatcher] Failed to send task to Kaggle queue: {e}", flush=True)
        return False

def search_uncontested_bounties(query: str, limit: int = 15) -> List[dict]:
    try:
        res = subprocess.run(
            ["gh", "search", "issues", query, "--state", "open", "--limit", str(limit), "--json", "repository,number,title,body,url,labels,commentsCount"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return []

DYNAMIC_BOUNTY_QUERIES = [
    'algora.io in:body state:open',
    'polar.sh in:body state:open',
    'label:bounty state:open',
    '"[BOUNTY]" state:open',
    'bounty "usdc" in:title,body state:open',
    'bounty "reward" in:title state:open'
]

def run_laptop_dispatcher_cycle():
    init_db()
    gh_token = get_gh_token()
    print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] Laptop Dispatcher: Scanning GitHub for Uncontested Bounties...", flush=True)

    dispatched_count = 0
    for q in DYNAMIC_BOUNTY_QUERIES:
        candidates = search_uncontested_bounties(q, limit=10)
        for cand in candidates:
            repo_info = cand.get("repository", {})
            repo = repo_info.get("nameWithOwner") if isinstance(repo_info, dict) else ""
            number = cand.get("number")
            title = cand.get("title", "")
            body = cand.get("body", "")
            comments_count = cand.get("commentsCount", 0)

            if not repo or not number:
                continue

            issue_id = f"{repo}#{number}"
            already_done, cur_status = is_issue_claimed_or_delivered(repo, number)
            if already_done:
                continue

            # 0. Genuine Code Issue Validation
            is_genuine, drop_reason = is_genuine_code_issue(repo, title, body)
            if not is_genuine:
                print(f"[DROP/NON_CODE] {issue_id}: {drop_reason}", flush=True)
                record_dispatch(repo, number, f"T-{issue_id}", f"REJECTED_NON_CODE: {drop_reason}")
                continue

            # 1. Zero-Competition Law Pre-Screen
            has_competing, comp_reason = has_competing_open_prs(repo, number)
            if has_competing:
                print(f"[DROP/COMPETITION] {issue_id}: {comp_reason}", flush=True)
                record_dispatch(repo, number, f"T-{issue_id}", f"REJECTED_COMPETITION: {comp_reason}")
                continue

            # 2. Package task for Kaggle Engine
            task_id = f"BT-{int(time.time())}-{repo.replace('/', '_')}-{number}"
            task_payload = {
                "task_id": task_id,
                "repo": repo,
                "issue_number": number,
                "title": title,
                "body": body,
                "wallet": SETTLEMENT_WALLET,
                "gh_token": gh_token,
                "created_at": time.time()
            }

            # 3. Offload to Kaggle Queue
            print(f"[OFFLOAD -> KAGGLE] Dispatching uncontested {issue_id} to Kaggle Cloud Engines...", flush=True)
            ok = dispatch_task_to_kaggle(task_payload)
            if ok:
                record_dispatch(repo, number, task_id, "Dispatched to Kaggle Fleet")
                dispatched_count += 1
                print(f" -> {issue_id} queued on Cloudflare KV. Engine will execute on Kaggle cloud.", flush=True)

        time.sleep(2)

    print(f"[Dispatcher Cycle Complete] Dispatched: {dispatched_count} uncontested tasks to Kaggle.\n", flush=True)

def main():
    print("=============================================================")
    print("⚡ LAPTOP LIGHTWEIGHT BOUNTY DISPATCHER (0% LOCAL CPU)")
    print("Role: GitHub Issue Search & Zero-Competition Triage")
    print("Execution Target: 5 Autonomous Kaggle Engines")
    print("=============================================================")
    while True:
        try:
            run_laptop_dispatcher_cycle()
        except Exception as e:
            print(f"[Dispatcher Error]: {e}", flush=True)
        time.sleep(180) # 3 min between sweeps

if __name__ == "__main__":
    main()
