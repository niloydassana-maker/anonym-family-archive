#!/usr/bin/env python3
"""
P0 KDP Select Enrollment Checker
Checks KDP Select enrollment status for all 8 eBooks via UIA-automated Chrome.
Logs results to war-log/kdp-lane.json and creates PNG evidence in war-log/evidence/L3/
"""

import json
import time
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import uiautomation as auto
except ImportError:
    print("ERROR: uiautomation not installed. Run: pip install uiautomation")
    sys.exit(1)

STATE_FILE = Path(r"D:\anonym\war-log\kdp-lane.json")
EVIDENCE_DIR = Path(r"D:\anonym\war-log\evidence\L3")

ASINS = [
    ("B0HHS6M3R4", "08 Kolkata Diaries", 4.99),
    ("B0GY4LS1DL", "01 Beyond Parameter Scaling", 5.99),
    ("B0HHP8FH1R", "02 Ground Beneath the Eagle", 4.99),
    ("B0HHQPZWGX", "03 The Beholder: Between Fullness and Emptiness", 5.99),
    ("B0HHWRNYH5", "04 Confession of the Ordinary, Companion", 0.99),
    ("B0H4RPLN3Q", "05 Confession of the Ordinary (flagship)", 5.99),
    ("B0HHTGBZRX", "06 Confession of the Recorder", 5.99),
    ("B0HHTFP15J", "07 Time Travels", 2.99),
]

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8-sig') as f:
        json.dump(state, f, indent=2)

def take_screenshot(name):
    """Capture full screen and save as PNG."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = EVIDENCE_DIR / f"{name}-{timestamp}.png"
    try:
        import pyautogui
        pyautogui.screenshot(str(path))
        print(f"  Screenshot saved: {path}")
        return str(path)
    except Exception as e:
        print(f"  Screenshot failed: {e}")
        return None

def find_control(parent, condition, max_depth=10):
    """Find control using auto.FindControl with condition function."""
    def compare(c, depth):
        return condition(c)
    return auto.FindControl(parent, compare, maxDepth=max_depth)

def find_kdp_window():
    """Find the Chrome window/tab with kdp.amazon.com."""
    for win in auto.GetRootControl().GetChildren():
        if win.ClassName == "Chrome_WidgetWin_1":
            # Check tab title
            tab_bar = find_control(win, lambda c: c.ClassName == "TabStrip")
            if tab_bar:
                for tab in tab_bar.GetChildren():
                    name = tab.Name or ""
                    if "kdp.amazon.com" in name.lower() or "kindle direct" in name.lower():
                        return win, tab, name
    return None, None, None

def click_element(element, description):
    """Click element with verification."""
    if element is None:
        print(f"  FAIL: {description} - element not found")
        return False
    try:
        rect = element.BoundingRectangle
        if rect.width() > 0 and rect.height() > 0:
            element.Click()
            time.sleep(1)
            print(f"  OK: {description}")
            return True
    except Exception as e:
        print(f"  FAIL: {description} - {e}")
    return False

def check_enrollment_for_asin(asin, title, expected_price):
    """Check KDP Select enrollment for a single ASIN."""
    print(f"\nChecking: {title} ({asin})")
    
    win, tab, tab_name = find_kdp_window()
    if not win:
        print("  ERROR: No KDP Chrome window found")
        return "ERROR", None
    
    # Activate tab
    click_element(tab, f"Activate tab: {tab_name}")
    
    # Navigate to Bookshelf - find the title row
    bookshelf = find_control(win, lambda c: c.Name and "bookshelf" in c.Name.lower())
    if not bookshelf:
        # Try finding by table/grid
        bookshelf = find_control(win, lambda c: c.ControlTypeName in ("TableControl", "DataGridControl"))
    
    if not bookshelf:
        print("  ERROR: Bookshelf not found")
        return "ERROR", None
    
    # Find the row with our ASIN
    asin_element = find_control(bookshelf, lambda c: c.Name and asin in c.Name)
    if not asin_element:
        print(f"  ERROR: ASIN {asin} not found in Bookshelf")
        return "NOT-FOUND", None
    
    # Click the title to open details
    click_element(asin_element, f"Open {title}")
    time.sleep(2)
    
    # Navigate to "Promote and advertise"
    promote_btn = find_control(win, lambda c: c.Name and "promote" in c.Name.lower() and "advertise" in c.Name.lower())
    if not promote_btn:
        promote_btn = find_control(win, lambda c: c.Name and "promote" in c.Name.lower())
    
    if not click_element(promote_btn, "Open Promote and advertise"):
        return "ERROR", None
    
    time.sleep(2)
    
    # Check for KDP Select enrollment status
    select_status = find_control(win, lambda c: c.Name and "kdp select" in c.Name.lower())
    if not select_status:
        select_status = find_control(win, lambda c: c.Name and "select" in c.Name.lower() and ("enrolled" in c.Name.lower() or "not enrolled" in c.Name.lower()))
    
    if select_status:
        status_text = select_status.Name or ""
        print(f"  Select status: {status_text}")
        enrolled = "enrolled" in status_text.lower() and "not" not in status_text.lower()
        
        # Take screenshot
        screenshot = take_screenshot(f"select-P0-{asin}")
        
        if not enrolled:
            # Try to enroll
            enroll_btn = find_control(win, lambda c: c.Name and "enroll" in c.Name.lower() and "free" in c.Name.lower())
            if enroll_btn:
                print("  Attempting enrollment...")
                click_element(enroll_btn, "Click Enroll for Free")
                time.sleep(3)
                # Re-check
                select_status2 = find_control(win, lambda c: c.Name and "kdp select" in c.Name.lower())
                if select_status2:
                    status_text2 = select_status2.Name or ""
                    enrolled = "enrolled" in status_text2.lower() and "not" not in status_text2.lower()
                    print(f"  After enrollment: {status_text2}")
                    take_screenshot(f"select-P0-{asin}-after-enroll")
        
        return "Y" if enrolled else "N", screenshot
    else:
        print("  WARNING: Could not find Select status element")
        return "UNKNOWN", take_screenshot(f"select-P0-{asin}-no-status")

def main():
    print("=" * 60)
    print("P0 KDP SELECT ENROLLMENT CHECK")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    state = load_state()
    
    # Update session status
    state["active_session_status"] = "UIA-SIGHTED"
    state["last_tick"] = datetime.now(timezone.utc).isoformat()
    
    enrollment_results = {}
    all_screenshots = []
    
    for asin, title, price in ASINS:
        status, screenshot = check_enrollment_for_asin(asin, title, price)
        enrollment_results[asin] = status
        if screenshot:
            all_screenshots.append(screenshot)
        
        # Log action
        state.setdefault("action_log", []).append({
            "t": datetime.now(timezone.utc).isoformat(),
            "asin": asin,
            "action": "P0_select_check",
            "evidence": screenshot or "",
            "result": status
        })
    
    # Update state
    state["select_enrollment"].update(enrollment_results)
    state["select_enrollment"]["checked_at"] = datetime.now(timezone.utc).isoformat()
    state["stale"]["select_enrollment"] = datetime.now(timezone.utc).isoformat()
    state["queue_status"]["evidence_count"] = len(all_screenshots)
    
    save_state(state)
    
    # Print summary
    print("\n" + "=" * 60)
    print("P0 ENROLLMENT SUMMARY")
    print("=" * 60)
    for asin, title, _ in ASINS:
        status = enrollment_results.get(asin, "ERROR")
        print(f"  {title} ({asin}): {status}")
    
    # Check if P1 gate passes (B0HHS6M3R4 enrolled)
    p1_gate = enrollment_results.get("B0HHS6M3R4") == "Y"
    print(f"\nP1 GATE (B0HHS6M3R4 enrolled): {'PASS' if p1_gate else 'FAIL'}")
    
    if not p1_gate:
        print("  ACTION REQUIRED: Enroll Kolkata Diaries in KDP Select before Sep 15")
        print("  Without enrollment, Countdown Deal cannot be created.")
    
    print(f"\nState saved to: {STATE_FILE}")
    print(f"Screenshots saved to: {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()