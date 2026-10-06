import sys
import os
import time
import json
import re
import subprocess

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

PASSWORD = "KiloBaba2026!#Wire"
EMAIL = "isearch.xsolve@gmail.com"

def eval_js(client, code):
    c = code.strip()
    if c.startswith('() =>') and not c.endswith(')()'):
        c = f"({c})()"
    elif not (c.startswith('(') and c.endswith(')()')):
        if not c.startswith('('):
            c = f"(() => {{ {c} }})()"
            
    res = client.execute_script(c)
    if isinstance(res, dict) and 'content' in res:
        for item in res.get('content', []):
            if isinstance(item, dict) and item.get('type') == 'text':
                try:
                    return json.loads(item.get('text', '{}'))
                except Exception:
                    return item.get('text')
    return res

def ensure_active_tab(client):
    try:
        tabs = client.list_tabs()
        if tabs:
            tab_id = tabs[0].get('id')
            client.switch_tab(tab_id)
            time.sleep(1)
            return tab_id
    except Exception as e:
        print("ensure_active_tab warning:", e)
    return None

def fetch_sms_otp():
    devices = ["10BE8135QM001KK", "G2866620341C0402558"]
    adb_path = r"D:\anonym\platform-tools\adb.exe"
    for dev in devices:
        try:
            cmd = [adb_path, "-s", dev, "shell", "content", "query", "--uri", "content://sms/inbox", "--projection", "address:body:date", "--sort", "date DESC"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            lines = res.stdout.splitlines()[:5]
            for line in lines:
                if "twilio" in line.lower() or "verification" in line.lower() or "code" in line.lower():
                    m = re.search(r'\b\d{6}\b', line)
                    if m:
                        return m.group(0)
        except Exception as e:
            pass
    return None

def main():
    print("=" * 60)
    print("TWILIO LOGIN MASTER: ACTIVE-TAB FOCUSED FLOW")
    print("=" * 60)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://www.twilio.com/login ...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(3)
        ensure_active_tab(client)
        
        print("[2] Filling email and clicking Continue...")
        client.fill("#email", EMAIL)
        time.sleep(1)
        client.click("#email-next")
        
        # 3. Wait for password screen
        print("[3] Waiting for password screen (login.twilio.com/u/login)...")
        for i in range(15):
            url_res = eval_js(client, "() => window.location.href")
            url = url_res.get('result', '') if isinstance(url_res, dict) else str(url_res)
            if "login.twilio.com/u/login" in url:
                break
            time.sleep(1)
            
        time.sleep(3)
        # Crucial: activate tab on password screen!
        ensure_active_tab(client)
        print("[+] Tab explicitly activated and window focused.")
        
        # 4. Fill confirmed password using real CDP keyboard fill
        print(f"[4] Setting confirmed password via client.fill: {PASSWORD} ...")
        fill_res = client.fill('input[type="password"]', PASSWORD)
        print("Password fill res:", fill_res)
        time.sleep(1)
        
        # 5. Wait for Turnstile
        print("[5] Waiting 5 seconds for Turnstile in focused active tab...")
        time.sleep(5)
        
        # 6. Click Turnstile checkbox at (557, 445)
        print("[6] Clicking Turnstile checkbox at (557, 445)...")
        c_res = client.call_tool('browser_click_xy', {'x': 557, 'y': 445})
        print("  Click res:", c_res)
        time.sleep(4)
        
        client.screenshot("D:/anonym/master_before_submit.png")
        print("[+] Screenshot: D:/anonym/master_before_submit.png")
        
        # 7. Submit form
        print("[7] Submitting form via Continue button & Enter key...")
        client.click('button[type="submit"]')
        time.sleep(0.5)
        client.press_key("Enter")
        
        print("[8] Waiting 15 seconds for console redirect / 2FA...")
        time.sleep(15)
        
        client.screenshot("D:/anonym/master_after_submit.png")
        print("[+] Screenshot: D:/anonym/master_after_submit.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER SUBMISSION ---")
        print(content[:2500])
        print("--------------------------------")
        
        # 8. Check for 2FA / OTP
        if "verification" in content.lower() or "code" in content.lower() or "sms" in content.lower():
            print("[9] 2FA detected! Polling ADB for SMS OTP...")
            otp = None
            for attempt in range(10):
                otp = fetch_sms_otp()
                if otp:
                    print(f"  [+] Found SMS OTP via ADB: {otp}")
                    break
                time.sleep(3)
                
            if otp:
                print(f"[10] Entering OTP: {otp} ...")
                client.fill('input[type="text"]', otp)
                time.sleep(1)
                client.press_key("Enter")
                time.sleep(8)
                client.screenshot("D:/anonym/master_post_otp.png")
                print(client.get_content()[:1500])
                
    except Exception as e:
        print("Error during master login:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
