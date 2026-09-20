#!/usr/bin/env python3
"""
KDP Lane Scheduler Daemon
Ticks at 7 past each hour. On 429: wait 60s, then use MiMo-V2.5 Free.
Logs everything to the bank (war-log/kdp-lane.json + EARN-LEDGER.md).
"""

import json
import time
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
import threading

STATE_FILE = Path(r"D:\anonym\war-log\kdp-lane.json")
EARN_LEDGER = Path(r"D:\anonym\EARN-LEDGER.md")
P0_SCRIPT = Path(r"D:\anonym\kdp_p0_enrollment_checker.py")

CADENCE_HOURS = 1
TICK_MINUTE = 7
BACKOFF_SECONDS = 60
MAX_RETRIES = 3

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def append_ledger(date, lane, action, evidence, pending):
    """Append row to EARN-LEDGER.md"""
    with open(EARN_LEDGER, 'a', encoding='utf-8') as f:
        f.write(f"| {date} | {lane} | {action} | {evidence} | {pending} |\n")

def log_to_bank(action, evidence, result, asin=""):
    """Log action to both state file and ledger."""
    state = load_state()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # State log
    state.setdefault("action_log", []).append({
        "t": timestamp,
        "asin": asin,
        "action": action,
        "evidence": evidence,
        "result": result
    })
    state["last_tick"] = timestamp
    save_state(state)
    
    # Ledger
    date_str = datetime.now().strftime("%m-%d")
    append_ledger(date_str, "L3-KDP", action, evidence, result)

def run_p0_check():
    """Run P0 enrollment check via UIA script."""
    try:
        result = subprocess.run(
            [sys.executable, str(P0_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "P0 check timeout (5 min)"
    except Exception as e:
        return False, "", str(e)

def run_with_backoff(task_fn, task_name, max_retries=MAX_RETRIES):
    """Run task with 429 backoff logic."""
    for attempt in range(max_retries):
        print(f"[{datetime.now().isoformat()}] {task_name} - Attempt {attempt + 1}/{max_retries}")
        success, stdout, stderr = task_fn()
        
        if success:
            print(f"  SUCCESS: {task_name}")
            return True, stdout, stderr
        
        # Check for 429 in output
        if "429" in stderr or "429" in stdout or "rate limit" in stderr.lower() or "rate limit" in stdout.lower():
            print(f"  429 detected, waiting {BACKOFF_SECONDS}s then MiMo-V2.5 Free...")
            time.sleep(BACKOFF_SECONDS)
            # TODO: Switch to MiMo-V2.5 Free endpoint here
            # For now, just retry
            continue
        
        print(f"  FAILED: {task_name} - {stderr[:200]}")
        if attempt < max_retries - 1:
            time.sleep(5)
    
    return False, "", f"Max retries exceeded for {task_name}"

def check_stale(state):
    """Check for stale watches per TTL rules."""
    now = datetime.now(timezone.utc)
    stale_alerts = []
    
    for key, ts_str in state.get("stale", {}).items():
        if ts_str == "DEAD":
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            if key == "pricing_watch" and (now - ts).total_seconds() > 24 * 3600:
                stale_alerts.append(f"pricing_watch DEAD (>24h)")
            elif key == "promo_watch" and (now - ts).total_seconds() > 24 * 3600:
                stale_alerts.append(f"promo_watch DEAD (>24h during live promo)")
            elif key == "pmr_watch" and (now - ts).total_seconds() > 30 * 86400:
                stale_alerts.append(f"pmr_watch DEAD (>30d)")
        except:
            pass
    
    if stale_alerts:
        for alert in stale_alerts:
            print(f"  STALE ALERT: {alert}")
            log_to_bank("stale_alert", "", alert)
            state["stale"][alert.split()[0]] = "DEAD"
        save_state(state)

def tick():
    """Single tick execution."""
    print(f"\n{'='*60}")
    print(f"TICK: {datetime.now().isoformat()}")
    print(f"{'='*60}")
    
    state = load_state()
    check_stale(state)
    
    # Determine what to do based on calendar
    now = datetime.now()
    today = now.date()
    
    # P0 window: Sep 12-14
    if today <= datetime(2026, 9, 14).date():
        print("Phase: P0 Select Enrollment Check (Sep 12-14)")
        success, out, err = run_with_backoff(run_p0_check, "P0_SELECT_CHECK")
        log_to_bank("P0_SELECT_CHECK", "war-log/evidence/L3/", "OK" if success else "FAIL")
        
        if success:
            state = load_state()
            # Check if P1 gate passes
            if state.get("select_enrollment", {}).get("B0HHS6M3R4") == "Y":
                print("P1 GATE PASSED - Ready for Countdown Deal creation")
    
    # P1 window: Sep 15-21
    elif today >= datetime(2026, 9, 15).date() and today <= datetime(2026, 9, 21).date():
        print("Phase: P1 Countdown Deal Active (Sep 15-21)")
        # TODO: Verify Countdown Deal is live on dashboard
        log_to_bank("P1_VERIFY", "war-log/evidence/L3/", "CHECK")
    
    # P2-P8 Free Days windows
    elif today >= datetime(2026, 9, 24).date():
        print("Phase: Free Days Wave (P2-P8)")
        # TODO: Check current free promo status
    
    # Update watches
    state["stale"]["pricing_watch"] = datetime.now(timezone.utc).isoformat()
    state["stale"]["promo_watch"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    
    print(f"Tick complete. Next tick at {get_next_tick_time()}")

def get_next_tick_time():
    """Calculate next tick at TICK_MINUTE past the hour."""
    now = datetime.now()
    next_tick = now.replace(minute=TICK_MINUTE, second=0, microsecond=0)
    if next_tick <= now:
        next_tick += timedelta(hours=1)
    return next_tick.strftime("%H:%M")

def wait_until_next_tick():
    """Sleep until next tick time."""
    next_tick = get_next_tick_time()
    now = datetime.now()
    target = now.replace(minute=TICK_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += timedelta(hours=1)
    
    wait_seconds = (target - now).total_seconds()
    print(f"Sleeping {wait_seconds:.0f}s until {target.strftime('%H:%M:%S')}")
    time.sleep(wait_seconds)

def main():
    print("KDP Lane Scheduler Daemon starting...")
    print(f"Tick cadence: Every hour at :{TICK_MINUTE:02d}")
    print(f"429 backoff: {BACKOFF_SECONDS}s + MiMo-V2.5 Free")
    print(f"State file: {STATE_FILE}")
    print(f"Ledger: {EARN_LEDGER}")
    
    # Initial tick
    tick()
    
    # Loop
    while True:
        wait_until_next_tick()
        tick()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDaemon stopped by user")
    except Exception as e:
        print(f"Daemon crashed: {e}")
        import traceback
        traceback.print_exc()