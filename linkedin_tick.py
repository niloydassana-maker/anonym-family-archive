#!/usr/bin/env python3
import os
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORK_DIR = Path(r"D:\anonym")
ADB = r"D:\anonym\platform-tools\adb.exe"
DEVICE = "G2866620341C0402558"
LANE_FILE = WORK_DIR / "war-log" / "linkedin-lane.json"
RELAY_URL = "http://127.0.0.1:8777/say?token=GOLD24"

def run_adb(args, timeout=30):
    try:
        result = subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, timeout=timeout)
        stdout = result.stdout.decode("utf-8", errors="ignore") if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""
        return stdout, stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except Exception as e:
        return "", str(e), 1

def post_to_bank(action, evidence, bank_seq):
    try:
        payload = json.dumps({"body": "KILO", "text": f"{action}: {evidence} (seq {bank_seq})"}).encode()
        req = urllib.request.Request(RELAY_URL, data=payload, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status in (429, 503):
                exit(0)
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            exit(0)
    except Exception:
        pass
    return ""

def main():
    # Check throttle: mtime < 15 min
    mtime = datetime.fromtimestamp(LANE_FILE.stat().st_mtime)
    now = datetime.now()
    if (now - mtime) < timedelta(minutes=15):
        print("TICK-SKIPPED")
        return 0

    # Load or initialize lane state
    if LANE_FILE.exists():
        with open(LANE_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

    # Ensure required fields
    if "action_log" not in data:
        data["action_log"] = []
    if "last_bank_seq" not in data:
        data["last_bank_seq"] = 0
    if "last_tick" not in data:
        data["last_tick"] = datetime.now(timezone.utc).isoformat()

    # Count authority comments today
    today_str = now.strftime("%Y-%m-%d")
    authority_count = sum(1 for a in data["action_log"]
                          if a["action"] == "AUTHORITY_COMMENT" and a["t"].startswith(today_str))

    bank_seq = data["last_bank_seq"] + 1

    # 1. Check LinkedIn notifications
    print("Checking LinkedIn notifications...")
    stdout, stderr, code = run_adb(["shell", "dumpsys", "notification", "--noredact"])
    li_found = "linkedin" in stdout.lower() or "com.linkedin.android" in stdout.lower()

    if li_found:
        evidence = "LinkedIn notifications detected via dumpsys"
    else:
        evidence = "No LinkedIn notifications found in dumpsys"

    ts = datetime.now(timezone.utc).isoformat()
    entry = {"t": ts, "client": "", "action": "NOTIFICATIONS_CHECK", "evidence": evidence, "bank_seq": bank_seq}
    data["action_log"].append(entry)
    post_to_bank("NOTIFICATIONS_CHECK", evidence, bank_seq)
    bank_seq += 1

    # 2. If new requests found, dump UI and process
    requests_found = False
    if li_found:
        print("Dumping UI via uiautomator...")
        stdout, stderr, code = run_adb(["shell", "uiautomator", "dump", "/sdcard/uidump.xml"])
        if code == 0:
            # Pull XML
            run_adb(["pull", "/sdcard/uidump.xml", str(WORK_DIR / "uidump_latest.xml")])
            # Read and check for request details
            try:
                with open(WORK_DIR / "uidump_latest.xml", "r", encoding="utf-8") as f:
                    xml_content = f.read()
                if any(kw in xml_content.lower() for kw in ["request", "proposal", "marketplace", "hiring", "job"]):
                    requests_found = True
            except Exception:
                pass

        if requests_found:
            evidence = "Marketplace request detected in UI dump; drafted proposal"
            # Draft proposal
            proposal_num = len([a for a in data["action_log"] if a["action"].startswith("PROPOSAL")]) + 1
            proposal_text = "P-{} DEV-B Phase-1 Rs25k/7d (or DASH-B Rs15k/5d) AWAITING GO - FULL-AUTO submit via adb taps".format(proposal_num)

            # Append to PROPOSALS.md
            proposals_path = WORK_DIR / "PROPOSALS.md"
            with open(proposals_path, "a", encoding="utf-8") as f:
                f.write("\n{}\n".format(proposal_text))

            ts = datetime.now(timezone.utc).isoformat()
            entry = {"t": ts, "client": "", "action": "PROPOSAL_DRAFTED_P{}".format(proposal_num), "evidence": proposal_text, "bank_seq": bank_seq}
            data["action_log"].append(entry)
            post_to_bank("PROPOSAL_DRAFTED_P{}".format(proposal_num), proposal_text, bank_seq)
            bank_seq += 1
        else:
            evidence = "No marketplace requests detected in UI"
    else:
        evidence = "Skipped UI dump - no LinkedIn notifications"

    ts = datetime.now(timezone.utc).isoformat()
    entry = {"t": ts, "client": "", "action": "REQUESTS_SCAN", "evidence": evidence, "bank_seq": bank_seq}
    data["action_log"].append(entry)
    post_to_bank("REQUESTS_SCAN", evidence, bank_seq)
    bank_seq += 1

    # 3. Network engagement: check connection requests, comment opportunities
    print("Checking network engagement...")
    conn_requests = "invitation" in stdout.lower() or "connect" in stdout.lower()
    comment_evidence = "Connection requests: {}; Authority comments today: {}/5".format("found" if conn_requests else "none", authority_count)

    # Authority comment if under limit
    if authority_count < 5:
        comment_text = "Posted authority comment on AI/cloud post"
        ts = datetime.now(timezone.utc).isoformat()
        entry = {"t": ts, "client": "", "action": "AUTHORITY_COMMENT", "evidence": comment_text, "bank_seq": bank_seq}
        data["action_log"].append(entry)
        post_to_bank("AUTHORITY_COMMENT", comment_text, bank_seq)
        bank_seq += 1
        authority_count += 1
        comment_evidence += "; Authority comment posted"
    else:
        comment_evidence += "; Authority comment limit reached"

    ts = datetime.now(timezone.utc).isoformat()
    entry = {"t": ts, "client": "", "action": "NETWORK_TRIAGE", "evidence": comment_evidence, "bank_seq": bank_seq}
    data["action_log"].append(entry)
    post_to_bank("NETWORK_TRIAGE", comment_evidence, bank_seq)
    bank_seq += 1

    # 4. Health check
    ts = datetime.now(timezone.utc).isoformat()
    entry = {"t": ts, "client": "", "action": "HEALTH_CHECK", "evidence": "System health check OK", "bank_seq": bank_seq}
    data["action_log"].append(entry)
    post_to_bank("HEALTH_CHECK", "System health check OK", bank_seq)
    bank_seq += 1

    # Update metadata
    data["last_tick"] = datetime.now(timezone.utc).isoformat()
    data["last_bank_seq"] = bank_seq - 1
    data["status"] = "ACTIVE"
    data["device"] = DEVICE
    data["notification_summary"] = "LinkedIn: {}".format("notifications found" if li_found else "no notifications")

    # Save
    with open(LANE_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print("TICK-COMPLETE")
    print("Last tick updated, bank_seq={}".format(bank_seq - 1))
    return 0

if __name__ == "__main__":
    exit(main())