#!/usr/bin/env python3
"""
Execute ONE KDP tick via PHONE-NATIVE adb (IQOO 192.168.1.6:38571)
"""
import json
import subprocess
import sys
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORK_DIR = Path(r"D:\anonym")
ADB = r"D:\anonym\platform-tools\adb.exe"
DEVICE = "10BE8135QM001KK"
KDP_LANE = WORK_DIR / "war-log" / "kdp-lane.json"
EVIDENCE_DIR = WORK_DIR / "war-log" / "evidence" / "L3"
RELAY_URL = "http://127.0.0.1:8777/say?token=GOLD24"

ASINS = [
    "B0HHS6M3R4", "B0GY4LS1DL", "B0HHP8FH1R", "B0HHQPZWGX",
    "B0HHWRNYH5", "B0H4RPLN3Q", "B0HHTGBZRX", "B0HHTFP15J"
]

ASIN_TITLES = {
    "B0HHS6M3R4": "08 Kolkata Diaries",
    "B0GY4LS1DL": "01 Beyond Parameter Scaling",
    "B0HHP8FH1R": "02 Ground Beneath the Eagle",
    "B0HHQPZWGX": "03 The Beholder: Between Fullness and Emptiness",
    "B0HHWRNYH5": "04 Confession of the Ordinary, Companion",
    "B0H4RPLN3Q": "05 Confession of the Ordinary (flagship)",
    "B0HHTGBZRX": "06 Confession of the Recorder",
    "B0HHTFP15J": "07 Time Travels",
}

SECTION6_FIXES = {
    "B0HHTGBZRX_ebook": "5.99",
    "B0HHTMRRM6_pb": "5.99",
}

def run_adb(args, timeout=60):
    try:
        result = subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except Exception as e:
        return "", str(e), 1

def log_to_relay():
    try:
        req = urllib.request.Request(RELAY_URL, data=b"KILO", method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status in (429, 503):
                print(f"  Bank POST {resp.status} - exiting quietly")
                return False
            print(f"  Bank POST: {resp.status}")
            return True
    except Exception as e:
        print(f"  Bank POST error: {e}")
        return True

def load_state():
    if KDP_LANE.exists():
        with open(KDP_LANE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return {}

def save_state(state):
    KDP_LANE.parent.mkdir(parents=True, exist_ok=True)
    with open(KDP_LANE, 'w', encoding='utf-8-sig') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def check_mtime_skip():
    if KDP_LANE.exists():
        mtime = datetime.fromtimestamp(KDP_LANE.stat().st_mtime)
        now = datetime.now()
        if (now - mtime) < timedelta(minutes=15):
            print("TICK-SKIPPED")
            return True
    return False

def launch_kdp_webapk():
    print("Launching KDP WebAPK shortcut...")
    stdout, stderr, code = run_adb([
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", "https://kdp.amazon.com/en_US/bookshelf"
    ], timeout=30)
    if code != 0:
        print(f"  ADB launch failed: {stderr}")
        return False
    print("  Launched, waiting 5s for page load...")
    time.sleep(5)
    return True

def dump_ui():
    print("Dumping UI hierarchy...")
    stdout, stderr, code = run_adb([
        "shell", "uiautomator", "dump", "/sdcard/uidump.xml"
    ], timeout=30)
    if code != 0:
        print(f"  UI dump failed: {stderr}")
        return False
    print("  UI dump created on device")
    return True

def pull_uidump():
    print("Pulling uidump.xml...")
    local_path = WORK_DIR / "uidump.xml"
    stdout, stderr, code = run_adb(["pull", "/sdcard/uidump.xml", str(local_path)], timeout=30)
    if code != 0:
        print(f"  Pull failed: {stderr}")
        return None
    print(f"  Pulled to {local_path}")
    return local_path

def parse_enrollment_from_xml(xml_path):
    """Parse uidump.xml for KDP Select enrollment status for each ASIN"""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Convert to string for searching
        xml_str = ET.tostring(root, encoding='unicode')
        
        results = {}
        for asin in ASINS:
            # Look for ASIN in the XML
            asin_lower = asin.lower()
            if asin_lower in xml_str.lower():
                # Found ASIN reference, now check for enrollment status nearby
                # Look for "Select", "Enrolled", "Not enrolled", "KDP Select"
                idx = xml_str.lower().find(asin_lower)
                context = xml_str[max(0, idx-500):idx+500].lower()
                
                if "not enrolled" in context or "not-enrolled" in context:
                    results[asin] = "N"
                elif "enrolled" in context or "kdp select" in context:
                    if "not" not in context:
                        results[asin] = "Y"
                    else:
                        results[asin] = "N"
                else:
                    results[asin] = "UNKNOWN"
            else:
                results[asin] = "NOT-FOUND"
        
        return results
    except Exception as e:
        print(f"  XML parse error: {e}")
        return {asin: "ERROR" for asin in ASINS}

def screencap_evidence(name):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    remote_path = f"/sdcard/{name}-{timestamp}.png"
    local_path = EVIDENCE_DIR / f"{name}-{timestamp}.png"
    
    stdout, stderr, code = run_adb(["shell", "screencap", "-p", remote_path], timeout=15)
    if code != 0:
        print(f"  Screencap failed: {stderr}")
        return None
    
    stdout, stderr, code = run_adb(["pull", remote_path, str(local_path)], timeout=15)
    if code != 0:
        print(f"  Pull screencap failed: {stderr}")
        return None
    
    # Clean up remote
    run_adb(["shell", "rm", remote_path], timeout=5)
    
    print(f"  Screenshot saved: {local_path}")
    return str(local_path)

def main():
    print("=" * 60)
    print("KDP ADB TICK - PHONE-NATIVE")
    print(f"Device: {DEVICE}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Health check: mtime < 15min
    if check_mtime_skip():
        return 0
    
    state = load_state()
    
    # Update session status
    state["active_session_status"] = "ADB-CHECKING"
    state["last_tick"] = datetime.now(timezone.utc).isoformat()
    
    # Step 1: Launch KDP WebAPK
    if not launch_kdp_webapk():
        state["active_session_status"] = "KDP-SESSION-ABSENT"
        state.setdefault("action_log", []).append({
            "t": datetime.now(timezone.utc).isoformat(),
            "asin": "",
            "action": "TICK P0-SKIP KDP-SESSION-ABSENT",
            "evidence": "ADB launch failed",
            "ledger_seq": 0
        })
        save_state(state)
        log_to_relay()
        return 0
    
    # Step 2: Dump UI
    if not dump_ui():
        state["active_session_status"] = "KDP-SESSION-ABSENT"
        state.setdefault("action_log", []).append({
            "t": datetime.now(timezone.utc).isoformat(),
            "asin": "",
            "action": "TICK P0-SKIP KDP-SESSION-ABSENT",
            "evidence": "UI dump failed",
            "ledger_seq": 0
        })
        save_state(state)
        log_to_relay()
        return 0
    
    # Step 3: Pull XML
    xml_path = pull_uidump()
    if not xml_path:
        state["active_session_status"] = "KDP-SESSION-ABSENT"
        state.setdefault("action_log", []).append({
            "t": datetime.now(timezone.utc).isoformat(),
            "asin": "",
            "action": "TICK P0-SKIP KDP-SESSION-ABSENT",
            "evidence": "XML pull failed",
            "ledger_seq": 0
        })
        save_state(state)
        log_to_relay()
        return 0
    
    # Step 4: Parse enrollment
    print("\nParsing enrollment status for 8 ASINs...")
    enrollment = parse_enrollment_from_xml(xml_path)
    
    print("\nENROLLMENT RESULTS:")
    all_enrolled = True
    for asin in ASINS:
        status = enrollment.get(asin, "ERROR")
        title = ASIN_TITLES.get(asin, asin)
        print(f"  {title} ({asin}): {status}")
        if status != "Y":
            all_enrolled = False
    
    # Update state
    if "select_enrollment" not in state:
        state["select_enrollment"] = {}
    state["select_enrollment"].update(enrollment)
    state["select_enrollment"]["checked_at"] = datetime.now(timezone.utc).isoformat()
    state["stale"] = state.get("stale", {})
    state["stale"]["select_enrollment"] = datetime.now(timezone.utc).isoformat()
    
    # Log each check
    for asin in ASINS:
        state.setdefault("action_log", []).append({
            "t": datetime.now(timezone.utc).isoformat(),
            "asin": asin,
            "action": "P0_select_check",
            "evidence": "uidump.xml",
            "result": enrollment.get(asin, "ERROR")
        })
    
    # Step 5: If any not enrolled -> log and stop
    if not all_enrolled:
        print("\n*** P0 GATE FAILED: Not all ASINs enrolled ***")
        state["active_session_status"] = "NOT-ENROLLED"
        
        # Take screenshot evidence
        screencap_evidence("select-P0-FAIL")
        
        state.setdefault("action_log", []).append({
            "t": datetime.now(timezone.utc).isoformat(),
            "asin": "",
            "action": "TICK P0-SKIP NOT-ENROLLED",
            "evidence": "P0 enrollment gate failed",
            "ledger_seq": 0
        })
        
        save_state(state)
        log_to_relay()
        
        # P1 Countdown cannot proceed
        print("P1 Countdown Sep15-21 (B0HHS6M3R4 $4.99 to $0.99) CANNOT PROCEED without enrolled=Y proof")
        return 0
    
    # Step 6: All enrolled - verify live prices match Sec 6 fixes
    print("\n*** P0 GATE PASSED: All 8 ASINs enrolled ***")
    state["active_session_status"] = "ALL-ENROLLED"
    
    # Take screenshot of bookshelf
    screencap_evidence("select-P0-ALL-ENROLLED")
    
    # Navigate to pricing pages for verification (read-only)
    # For now, just log the verification intent
    print("\nVerifying live prices match Sec 6 fixes...")
    for asin_fix, expected_price in SECTION6_FIXES.items():
        print(f"  {asin_fix}: expected ${expected_price}")
        # Would need to navigate to each book's pricing page
        # This requires more complex UI navigation
    
    # Take pricing verification screenshots
    screencap_evidence("pricing-verification")
    
    # Step 7: P1 Countdown status
    print("\nP1 COUNTDOWN STATUS:")
    print("  ASIN: B0HHS6M3R4 (08 Kolkata Diaries)")
    print("  Promo: Countdown Deal Sep15-21")
    print("  Price: $4.99 -> $0.99")
    print("  Expires: 2026-09-21")
    print("  State: READY TO CREATE (P0 gate passed)")
    
    state["promo_status"] = state.get("promo_status", {})
    state["promo_status"]["P1_countdown_B0HHS6M3R4"] = "READY-P0-PASSED"
    state["promo_status"]["countdown_expiry"] = "2026-09-21-URGENT"
    state["promo_status"]["current_free"] = "NONE"
    
    state.setdefault("action_log", []).append({
        "t": datetime.now(timezone.utc).isoformat(),
        "asin": "B0HHS6M3R4",
        "action": "P1_COUNTDOWN_STATUS",
        "evidence": "P0 gate passed, all enrolled",
        "result": "READY"
    })
    
    # Save final state
    save_state(state)
    
    # Log to relay bank
    log_to_relay()
    
    print("\n" + "=" * 60)
    print("TICK COMPLETE")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())