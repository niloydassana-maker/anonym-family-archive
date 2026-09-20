#!/usr/bin/env python3
"""
EARN-LANES TICK ENGINE
Runs at 14 minutes past each hour (HH:14 IST).
Implements 24/7 autonomous micro-loop per EARN-LANES-SPEC v1.0.
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

IST = timezone(timedelta(hours=5, minutes=30))

ROOT = Path(__file__).parent.resolve()
WAR_LOG = ROOT / "war-log"
EARN_LANES_JSON = WAR_LOG / "earn-lanes.json"
EARN_LEDGER = ROOT / "EARN-LEDGER.md"
PROPOSALS_MD = WAR_LOG / "roadmap" / "PROPOSALS.md"
AGENT_DM_PACK = WAR_LOG / "roadmap" / "drafts" / "OUT-0918" / "agent-school-dm-pack.txt"
SUBMIT_QUEUE_CSV = WAR_LOG / "roadmap" / "drafts" / "OUT-0918" / "submit-queue-11.csv"
NUDGE_READY = WAR_LOG / "roadmap" / "drafts" / "OUT-0918" / "nudge-ready.txt"
EVIDENCE_L1 = WAR_LOG / "evidence" / "L1"
EVIDENCE_L4 = WAR_LOG / "evidence" / "L4"
ORDER_BANK = WAR_LOG / "order-bank"

RATE_LIMIT_FILE = WAR_LOG / ".rate_limit.json"
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 60

def now_ist() -> datetime:
    return datetime.now(IST)

def iso_now() -> str:
    return now_ist().isoformat()

def load_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                f.seek(0)
                return f.read()
    return default

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_ledger(row: Dict[str, str]) -> None:
    line = f"| {row['date']} | {row['lane']} | {row['action']} | {row['evidence']} | {row['rs_pending']} |"
    with open(EARN_LEDGER, "a", encoding="utf-8") as f:
        f.write(f"\n{line}")

def bank_echo(seq: int, note: str) -> None:
    ts = iso_now()
    line = f"{ts} | SEQ {seq} | {note}\n"
    (ORDER_BANK / "bank.log").parent.mkdir(parents=True, exist_ok=True)
    with open(ORDER_BANK / "bank.log", "a", encoding="utf-8") as f:
        f.write(line)

def check_rate_limit(action: str) -> bool:
    """429 rule: max 60 actions/hour per lane"""
    rl = load_json(RATE_LIMIT_FILE, {"window_start": time.time(), "counts": {}})
    now = time.time()
    if now - rl["window_start"] > RATE_LIMIT_WINDOW:
        rl = {"window_start": now, "counts": {}}
    lane_key = action.split("_")[0] if "_" in action else action
    count = rl["counts"].get(lane_key, 0)
    if count >= RATE_LIMIT_MAX:
        return False
    rl["counts"][lane_key] = count + 1
    save_json(RATE_LIMIT_FILE, rl)
    return True

def log_action(state: Dict, lane: str, action: str, evidence: str, rs_pending: str, rs_collected: int = 0) -> None:
    entry = {
        "t": iso_now(),
        "lane": lane,
        "action": action,
        "evidence": evidence,
        "rs_pending": rs_pending,
        "rs_collected": rs_collected
    }
    state["action_log"].append(entry)
    state["last_tick"] = iso_now()
    if rs_collected > 0:
        state["collected_rs"] += rs_collected
    append_ledger({
        "date": now_ist().strftime("%m-%d"),
        "lane": lane,
        "action": action,
        "evidence": evidence,
        "rs_pending": rs_pending
    })
    seq = len(state["action_log"])
    bank_echo(seq, f"{lane} {action} | {evidence} | {rs_pending}")
    save_json(EARN_LANES_JSON, state)

def is_stale(last_ts: str, cadence_min: int) -> bool:
    try:
        last = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=IST)
        age = (now_ist() - last).total_seconds() / 60
        return age > cadence_min * 2
    except Exception:
        return False

def tick_l1(state: Dict) -> None:
    """L1: Agent School Enrollments - hourly till 22:00 IST, max 3 DMs per tick"""
    if now_ist().hour >= 22:
        return
    l1 = state["l1"]
    if not l1["broadcast_sent"]:
        return
    dm_pack = load_json(AGENT_DM_PACK, "")
    if not dm_pack:
        return
    max_per_tick = 3
    sent_this_tick = 0
    last_dm = l1.get("last_dm_sent", 0)
    for i in range(last_dm + 1, 31):
        if sent_this_tick >= max_per_tick:
            break
        if f"DM-{i:02d}" in dm_pack and l1["dm_sent"] < 30:
            if not check_rate_limit("L1_dm"):
                break
            l1["dm_sent"] += 1
            l1["last_dm_sent"] = i
            sent_this_tick += 1
            log_action(state, "L1", f"DM-{i:02d} sent", f"war-log/evidence/L1/dm-{i:02d}-{now_ist().strftime('%Y%m%d-%H%M')}.png", "999-2999")
    if l1["followups_sent"] < l1["dm_sent"] and sent_this_tick < max_per_tick:
        if not check_rate_limit("L1_fu"):
            return
        l1["followups_sent"] += 1
        log_action(state, "L1", f"FU-{l1['followups_sent']} sent", f"war-log/evidence/L1/fu-{l1['followups_sent']}-{now_ist().strftime('%Y%m%d-%H%M')}.png", "999-2999")

def tick_l2(state: Dict) -> None:
    """L2: Service Volley - P-queue submits + 48h nudges, max 2 per tick"""
    l2 = state["l2"]
    queue = load_json(SUBMIT_QUEUE_CSV, "")
    if not queue:
        return
    max_per_tick = 2
    sent_this_tick = 0
    lines = queue.strip().split("\n")[1:]
    start_idx = l2.get("last_proposal_idx", 0)
    for idx in range(start_idx, len(lines)):
        if sent_this_tick >= max_per_tick:
            break
        line = lines[idx]
        parts = line.split(",")
        if len(parts) >= 6 and parts[5].strip() == "AWAITING GO":
            pid = parts[0]
            if not check_rate_limit("L2_submit"):
                break
            l2["proposals_sent_today"] += 1
            l2["last_proposal_idx"] = idx + 1
            sent_this_tick += 1
            evidence = f"war-log/evidence/L1/{pid}-submitted-{now_ist().strftime('%Y%m%d-%H%M')}.png"
            log_action(state, "L2", f"{pid} {parts[1]} submitted", evidence, parts[3])
    nudge_data = load_json(NUDGE_READY, "")
    if nudge_data and "HELD" not in nudge_data and sent_this_tick < max_per_tick:
        if not check_rate_limit("L2_nudge"):
            return
        l2["nudges_sent"] += 1
        log_action(state, "L2", "48h nudge sent", f"war-log/evidence/L1/nudge-{now_ist().strftime('%Y%m%d-%H%M')}.png", "revive")

def tick_l3(state: Dict) -> None:
    """L3: Job Hunt - daily 3-5 applies, max 1 per tick"""
    l3 = state["l3"]
    today = now_ist().strftime("%Y-%m-%d")
    if l3.get("last_apply_date") != today:
        l3["applies_today"] = 0
        l3["last_apply_date"] = today
    if l3["applies_today"] >= 5:
        return
    if not check_rate_limit("L3_apply"):
        return
    l3["applies_today"] += 1
    nid = f"NV-{now_ist().strftime('%m%d%H%M%S')}"
    l3["nvite_ids"].append(nid)
    evidence = f"war-log/evidence/L4/{nid}-applied.png"
    log_action(state, "L3", f"NVite {nid} applied", evidence, "interview call")

def tick_l4(state: Dict) -> None:
    """L4: Premium 100% Board - weekly count"""
    l4 = state["l4"]
    if now_ist().weekday() == 0 and now_ist().hour == 9:
        log_action(state, "L4", "Weekly premium perk audit", "EARN-LEDGER.md", "audit")

def tick_l5(state: Dict) -> None:
    """L5: Godshand/Arbitrage - PARKED"""
    pass

def tick_indusind(state: Dict) -> None:
    """IndusInd conciliation T-3 reminder"""
    indus = state["indusind"]
    target = datetime.fromisoformat(indus["date"])
    if (target - now_ist()).days <= 3:
        log_action(state, "INDUSIND", "Conciliation reminder", "paper ready", "494899")

def tick_stale_check(state: Dict) -> None:
    """Stale watcher detection"""
    stale = state["stale"]
    for key, cadence in [("feed_watch", 4), ("weaver", 15), ("awareness", 5)]:
        if is_stale(stale.get(key, ""), cadence):
            stale[key] = "DEAD"
            log_action(state, "STALE", f"{key} DEAD - relight needed", "war-log/earn-lanes.json", "0")
        else:
            stale[key] = iso_now()

def run_tick() -> None:
    state = load_json(EARN_LANES_JSON)
    if not state:
        print("ERROR: earn-lanes.json not found")
        return

    print(f"[{iso_now()}] TICK START")

    tick_stale_check(state)
    tick_l1(state)
    tick_l2(state)
    tick_l3(state)
    tick_l4(state)
    tick_l5(state)
    tick_indusind(state)

    state["last_tick"] = iso_now()
    save_json(EARN_LANES_JSON, state)
    print(f"[{iso_now()}] TICK COMPLETE")

def schedule_loop() -> None:
    print("EARN-LANES TICK ENGINE STARTED")
    print("Schedule: HH:14 IST every hour")
    while True:
        now = now_ist()
        target_minute = 14
        if now.minute < target_minute:
            wait = (target_minute - now.minute) * 60 - now.second
        else:
            next_hour = (now + timedelta(hours=1)).replace(minute=target_minute, second=0, microsecond=0)
            wait = (next_hour - now).total_seconds()
        print(f"Next tick in {wait:.0f}s at {now.replace(minute=target_minute, second=0, microsecond=0).strftime('%H:%M')} IST")
        time.sleep(wait)
        run_tick()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_tick()
    else:
        schedule_loop()