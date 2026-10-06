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

def fetch_latest_twilio_otp():
    adb_path = r"d:\anonym\platform-tools\adb.exe"
    try:
        res = subprocess.run(
            [adb_path, "-s", "G2866620341C0402558", "shell", "content", "query", "--uri", "content://sms/inbox", "--projection", "address:body:date"],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=8
        )
        lines = res.stdout.split('Row: ')
        for line in lines[1:6]:
            if "twilio" in line.lower() or "verification" in line.lower():
                m = re.search(r'\b\d{6}\b', line)
                if m:
                    return m.group(0)
    except Exception as e:
        print("Error fetching OTP via adb:", e)
    return None

def main():
    print("=" * 60)
    print("TWILIO LOGIN: FULL MFA SUBMISSION & CONSOLE ACCESS")
    print("=" * 60)
    
    # 1. Bring Chrome to front
    ps_cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('Chrome')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://www.twilio.com/login ...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(4)
        ensure_active_tab(client)
        
        # Check if we are already logged in or on MFA screen
        curr_url = eval_js(client, "() => window.location.href")
        print("Current URL:", curr_url)
        
        if "console.twilio.com" in str(curr_url):
            print("[+] Already on console.twilio.com!")
        else:
            # Need to login
            print("[2] Filling email and clicking Continue...")
            client.fill("#email", EMAIL)
            time.sleep(1)
            client.click("#email-next")
            
            # Wait for password screen
            print("[3] Waiting for password screen...")
            for i in range(15):
                url_res = eval_js(client, "() => window.location.href")
                url = url_res.get('result', '') if isinstance(url_res, dict) else str(url_res)
                if "login.twilio.com/u/login" in url or "mfa-sms-challenge" in url:
                    break
                time.sleep(1)
                
            time.sleep(3)
            ensure_active_tab(client)
            
            # If on password screen
            curr_url = eval_js(client, "() => window.location.href")
            if "login.twilio.com/u/login" in str(curr_url):
                print(f"[4] Setting confirmed password: {PASSWORD} ...")
                client.fill('input[type="password"]', PASSWORD)
                time.sleep(2)
                
                print("[5] Clicking Turnstile at (557, 445)...")
                client.call_tool('browser_click_xy', {'x': 557, 'y': 445})
                time.sleep(4)
                
                print("[6] Submitting password...")
                client.click('button[type="submit"]')
                time.sleep(0.5)
                client.press_key("Enter")
                
                print("[7] Waiting 10 seconds for MFA challenge screen...")
                time.sleep(10)
                ensure_active_tab(client)
                
        # Now we should be on mfa-sms-challenge or console
        content = client.get_content()
        client.screenshot("D:/anonym/twilio_mfa_screen.png")
        print("[+] Screenshot: D:/anonym/twilio_mfa_screen.png")
        print("Content Summary:", content[:600])
        
        if "code" in content.lower() or "mfa" in content.lower() or "challenge" in content.lower():
            print("[8] MFA Screen Confirmed! Polling for fresh OTP from Nokia...")
            otp = None
            for attempt in range(12):
                otp = fetch_latest_twilio_otp()
                print(f"  Attempt {attempt+1}/12: OTP = {otp}")
                if otp:
                    break
                time.sleep(3)
                
            if otp:
                print(f"[9] Entering OTP {otp} into MFA field...")
                # Check remember checkbox if present
                eval_js(client, """
                    () => {
                        const cb = document.querySelector('input[type="checkbox"]');
                        if (cb && !cb.checked) cb.click();
                    }
                """)
                time.sleep(0.5)
                
                # Fill OTP into input
                client.fill('input[type="text"], input[name="code"], #code', otp)
                time.sleep(1)
                
                print("[10] Submitting MFA code...")
                client.click('button[type="submit"]')
                time.sleep(0.5)
                client.press_key("Enter")
                
                print("[11] Waiting 15 seconds for Console to load...")
                time.sleep(15)
                ensure_active_tab(client)
                
                client.screenshot("D:/anonym/twilio_console_final.png")
                print("[+] Console Screenshot: D:/anonym/twilio_console_final.png")
                
                final_content = client.get_content()
                print("\n================ CONSOLE PAGE CONTENT ================")
                print(final_content[:3000])
                print("======================================================")
                
    except Exception as e:
        print("Error during MFA login flow:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
