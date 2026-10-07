#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn "Open to Work" Search + Connect Automation
Uses Agent360 MCP (@agent360/browser-mcp) on Chrome Profile 17
"""

import sys
import os
import time
import json
import io
import base64
import subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
SHOTS_DIR = HERE / "shots"
SHOTS_DIR.mkdir(exist_ok=True)

# Agent360 client
sys.path.insert(0, str(HERE))
from agent360_client import Agent360Client

# Relay config
RELAY_URL = "http://127.0.0.1:8777/hear?token=GOLD24"

# Note template (ASCII only)
CONNECT_NOTE = (
    "Saw you're Open to Work. Built job automation applying to perfect-fit roles "
    "on LinkedIn/Naukri/Foundit while laptop idles (Rs 499 setup). Demo: "
    "https://drive.google.com/file/d/1ToXMovfWEuqRBBRwyJpNxbgUVfQMoAOl/view?usp=sharing. "
    "Happy to share more if you accept. - Kunal"
)

SEARCH_URL = (
    "https://www.linkedin.com/search/results/people/"
    "?keywords=open%20to%20work&origin=GLOBAL_SEARCH_HEADER"
)

MAX_CONNECTS_PER_RUN = 15
GAP_BETWEEN_CONNECTS = 12  # seconds
GAP_AFTER_PAGE = 60  # seconds


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(HERE / "kilo-say.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def report_to_relay(body: str, text: str):
    try:
        import urllib.request
        data = json.dumps({"body": body, "text": text}).encode("utf-8")
        req = urllib.request.Request(RELAY_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            log(f"[RELAY OK] {text[:80]}")
    except Exception as e:
        log(f"[RELAY WARN] {e}")


def screenshot(client: Agent360Client, name: str) -> str:
    """Take screenshot via Agent360."""
    try:
        path = SHOTS_DIR / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        r = client.call_tool("browser_take_screenshot", {
            "format": "png",
            "fullPage": True,
            "filePath": str(path)
        })
        log(f"Screenshot saved: {path}")
        return str(path)
    except Exception as e:
        log(f"Screenshot failed: {e}")
        return ""


def find_connect_buttons(client: Agent360Client):
    """Find all Connect buttons on the current page with their profile context."""
    script = """(() => {
        const cards = document.querySelectorAll(
            '.entity-result, .reusable-search__result-container, '
            + '[data-test-search-result], [data-view-name*="search-result"], '
            + '.search-result__wrapper'
        );
        const results = [];
        cards.forEach((card, idx) => {
            // Find name
            const nameEl = card.querySelector(
                '.entity-result__title-text a, [class*="name"] a[href*="/in/"], '
                + 'a.app-aware-link[href*="/in/"]'
            );
            const name = nameEl ? nameEl.innerText.trim() : '';
            
            // Find Connect button in this card
            const connectBtn = card.querySelector(
                'button[aria-label*="Connect" i], '
                + 'button:has-text("Connect"), '
                + '[role="button"][aria-label*="Connect" i]'
            );
            
            if (connectBtn) {
                const rect = connectBtn.getBoundingClientRect();
                results.push({
                    idx,
                    name,
                    hasConnect: true,
                    btnX: Math.round(rect.x + rect.width / 2),
                    btnY: Math.round(rect.y + rect.height / 2),
                    btnW: Math.round(rect.width),
                    btnH: Math.round(rect.height),
                    btnAria: connectBtn.getAttribute('aria-label') || '',
                    btnText: connectBtn.innerText.trim()
                });
            } else {
                results.push({
                    idx,
                    name,
                    hasConnect: false
                });
            }
        });
        return results;
    })()"""
    r = client.call_tool("browser_execute_script", {"code": script})
    content = r.get("content", [])
    for item in content:
        if item.get("type") == "text":
            try:
                parsed = json.loads(item.get("text", ""))
                if isinstance(parsed, dict) and "result" in parsed:
                    return parsed["result"]
            except Exception:
                pass
    return []


def click_connect_and_fill_note(client: Agent360Client, btn_x: int, btn_y: int, profile_name: str):
    """Click Connect button, handle modal, fill note, send."""
    # Click Connect button via coordinates
    script_click = f"""(() => {{
        const el = document.elementFromPoint({btn_x}, {btn_y});
        if (el) {{
            el.click();
            return {{clicked: true}};
        }}
        return {{clicked: false}};
    }})()"""
    r = client.call_tool("browser_execute_script", {"code": script_click})
    time.sleep(2)

    # Check for "Add a note" in modal
    script_modal = """(() => {
        const dialog = document.querySelector('[role="dialog"], .artdeco-modal');
        if (!dialog) return {found: false};
        const addNoteBtn = Array.from(dialog.querySelectorAll('button, span')).find(
            el => (el.innerText || '').toLowerCase().includes('add a note') ||
                   (el.getAttribute('aria-label') || '').toLowerCase().includes('add a note')
        );
        if (addNoteBtn) {
            addNoteBtn.click();
            return {found: true, step: 'add_note_clicked'};
        }
        // Check if textarea already visible
        const textarea = dialog.querySelector('textarea[name="message"], textarea[placeholder*="note" i]');
        if (textarea) return {found: true, step: 'textarea_visible'};
        return {found: true, step: 'dialog_open'};
    })()"""
    r = client.call_tool("browser_execute_script", {"code": script_modal})
    time.sleep(1)

    # Fill note and send
    script_fill = f"""(() => {{
        const dialog = document.querySelector('[role="dialog"], .artdeco-modal');
        if (!dialog) return {{status: 'no_dialog'}};
        
        const textarea = dialog.querySelector(
            'textarea[name="message"], textarea[placeholder*="note" i], textarea[aria-label*="note" i]'
        );
        if (textarea) {{
            textarea.focus();
            textarea.value = `{CONNECT_NOTE}`;
            textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
            textarea.dispatchEvent(new Event('change', {{bubbles: true}}));
            
            // Find Send button
            const sendBtn = Array.from(dialog.querySelectorAll('button')).find(
                btn => (btn.innerText || '').toLowerCase() === 'send' ||
                       (btn.getAttribute('aria-label') || '').toLowerCase().includes('send')
            );
            if (sendBtn && !sendBtn.disabled) {{
                sendBtn.click();
                return {{status: 'sent'}};
            }}
            return {{status: 'filled_no_send'}};
        }}
        return {{status: 'no_textarea'}};
    }})()"""
    r = client.call_tool("browser_execute_script", {"code": script_fill})
    time.sleep(2)
    
    return r


def process_page(client: Agent360Client, page_num: int, sent_count: int):
    """Process one page of search results."""
    log(f"=== Processing page {page_num} ===")
    
    # Find Connect buttons
    buttons = find_connect_buttons(client)
    connectable = [b for b in buttons if b.get("hasConnect")]
    log(f"Found {len(connectable)} Connect buttons on page {page_num}")
    
    for btn in connectable:
        if sent_count >= MAX_CONNECTS_PER_RUN:
            log(f"Reached max connects ({MAX_CONNECTS_PER_RUN})")
            return sent_count, True
        
        name = btn.get("name", f"profile_{btn['idx']}")
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()[:40]
        
        log(f"\n--- [{sent_count+1}/{MAX_CONNECTS_PER_RUN}] {name} ---")
        
        # Click Connect and fill note
        result = click_connect_and_fill_note(client, btn["btnX"], btn["btnY"], name)
        log(f"Connect result: {result}")
        
        # Screenshot receipt
        shot = screenshot(client, f"connect_{safe_name}")
        
        # Verify send
        content = result.get("content", [])
        sent = False
        for item in content:
            if item.get("type") == "text":
                try:
                    parsed = json.loads(item.get("text", ""))
                    if isinstance(parsed, dict) and "result" in parsed:
                        if parsed["result"].get("status") == "sent":
                            sent = True
                except Exception:
                    pass
        
        if sent:
            sent_count += 1
            receipt = f"[CONNECT SENT {sent_count}/{MAX_CONNECTS_PER_RUN}] {name} | Shot: {shot}"
            log(receipt)
            report_to_relay("KILO", receipt)
        else:
            log(f"Connect may have failed for {name}")
        
        if sent_count < MAX_CONNECTS_PER_RUN:
            log(f"Waiting {GAP_BETWEEN_CONNECTS}s...")
            time.sleep(GAP_BETWEEN_CONNECTS)
    
    return sent_count, False


def click_next_page(client: Agent360Client) -> bool:
    """Click Next pagination button."""
    script = """(() => {
        const nextBtn = document.querySelector(
            'button[aria-label*="Next" i], button:has-text("Next"), '
            + '.artdeco-pagination__button--next, button[data-test-pagination-next]'
        );
        if (nextBtn && !nextBtn.disabled) {
            nextBtn.click();
            return {clicked: true};
        }
        return {clicked: false};
    })()"""
    r = client.call_tool("browser_execute_script", {"code": script})
    content = r.get("content", [])
    for item in content:
        if item.get("type") == "text":
            try:
                parsed = json.loads(item.get("text", ""))
                if isinstance(parsed, dict) and "result" in parsed:
                    return parsed["result"].get("clicked", False)
            except Exception:
                pass
    return False


def main():
    log("=== LINKEDIN CONNECT AUTOMATION START ===")
    report_to_relay("KILO", "LinkedIn Connect automation started")
    
    client = Agent360Client()
    client.start()
    
    try:
        # Navigate to search
        log(f"Navigating to: {SEARCH_URL}")
        client.call_tool("browser_navigate", {"url": SEARCH_URL})
        time.sleep(8)
        
        sent_count = 0
        page_num = 1
        stop = False
        
        while not stop and sent_count < MAX_CONNECTS_PER_RUN:
            sent_count, stop = process_page(client, page_num, sent_count)
            
            if not stop and sent_count < MAX_CONNECTS_PER_RUN:
                log("Clicking Next page...")
                if click_next_page(client):
                    page_num += 1
                    time.sleep(GAP_AFTER_PAGE)
                else:
                    log("No Next button or disabled - stopping")
                    break
            else:
                break
        
        log(f"\n=== COMPLETE: {sent_count}/{MAX_CONNECTS_PER_RUN} CONNECTS SENT ===")
        report_to_relay("KILO", f"LinkedIn Connect automation complete: {sent_count} sent")
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        report_to_relay("KILO", f"Connect automation ERROR: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()