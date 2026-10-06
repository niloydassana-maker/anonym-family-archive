import sys
import os
import time

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("=" * 60, flush=True)
    print("TWILIO LOGIN: REAL KEYBOARD FILL VIA AGENT360", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    print("[+] Agent360 Client started.", flush=True)
    
    try:
        print("[1] Navigating to https://login.twilio.com/u/login ...", flush=True)
        client.navigate("https://login.twilio.com/u/login")
        time.sleep(4)
        
        print("[2] Filling #email with browser_fill...", flush=True)
        fill_res = client.fill("#email", "isearch.xsolve@gmail.com")
        print("  Fill res:", fill_res, flush=True)
        time.sleep(1)
        
        print("[3] Clicking #email-next with browser_click...", flush=True)
        click_res = client.click("#email-next")
        print("  Click res:", click_res, flush=True)
        
        print("[4] Waiting 6 seconds for password / next screen...", flush=True)
        time.sleep(6)
        
        client.screenshot(r"D:\anonym\twilio_login_step3_after_fill.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_login_step3_after_fill.png", flush=True)
        
        content = client.get_content()
        print("--- PAGE CONTENT AFTER SUBMISSION ---", flush=True)
        print(content[:1500], flush=True)
        print("-------------------------------------", flush=True)

    except Exception as e:
        print("Error during fill/click:", e, flush=True)
    finally:
        client.close()
        print("[*] Agent360 client closed.", flush=True)

if __name__ == "__main__":
    main()
