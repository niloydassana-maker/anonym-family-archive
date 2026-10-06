import sys
import os
import time
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    PHONE = "9830739230"
    print("=" * 60, flush=True)
    print(f"SUBMITTING PHONE {PHONE} FOR TWILIO SMS VERIFICATION", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    
    try:
        tabs = client.list_tabs()
        print(f"Found {len(tabs)} tabs:")
        mfa_tab = None
        for t in tabs:
            url = t.get("url", "")
            title = t.get("title", "")
            tid = t.get("id")
            print(f"  Tab {tid}: {url[:70]} | {title[:40]}")
            if "unified-mfa" in url or "Two-factor" in title or "twilio.com" in url:
                mfa_tab = tid
                
        if mfa_tab:
            print(f"Switching to MFA tab: {mfa_tab}...")
            client.switch_tab(mfa_tab)
            time.sleep(1)
        else:
            print("MFA tab not in list_tabs, checking current page content...")
            
        print(f"Filling #phone-input with {PHONE}...")
        fill_res = client.fill("#phone-input", PHONE)
        print("Fill result:", json.dumps(fill_res, ensure_ascii=True))
        time.sleep(1)
        
        print("Clicking #send-sms-btn...")
        click_res = client.click("#send-sms-btn")
        print("Click result:", json.dumps(click_res, ensure_ascii=True))
        
        time.sleep(4)
        client.screenshot(r"D:\anonym\twilio_sms_sent_success.png")
        print("Saved screenshot to D:\\anonym\\twilio_sms_sent_success.png")
        
        # Get page content to verify SMS was sent
        content = client.get_content()
        print("Page content preview:")
        print(content[:500])
        
    except Exception as e:
        print("Error during execution:", repr(e))
    finally:
        client.close()
        print("Agent360 client closed.")

if __name__ == "__main__":
    main()
