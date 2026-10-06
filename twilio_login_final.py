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
    print("TWILIO FINAL LOGIN WITH NEW PASSWORD & ADB OTP")
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
        
        print("[2] Filling email and clicking Continue...")
        client.fill("#email", EMAIL)
        time.sleep(1)
        client.click("#email-next")
        
        # 3. Wait for password screen
        print("[3] Waiting for password screen...")
        for i in range(12):
            url_res = eval_js(client, "() => window.location.href")
            url = url_res.get('result', '') if isinstance(url_res, dict) else str(url_res)
            if "login.twilio.com/u/login" in url:
                break
            time.sleep(1)
            
        time.sleep(4)
        
        # 4. Fill NEW password
        print(f"[4] Filling confirmed password: {PASSWORD} ...")
        eval_js(client, f"""
            () => {{
                const pw = document.querySelector('input[type="password"]');
                if (pw) {{
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(pw, "{PASSWORD}");
                    pw.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    pw.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
        """)
        time.sleep(1)
        
        # 5. Wait for Turnstile
        print("[5] Waiting 5 seconds for Turnstile...")
        time.sleep(5)
        
        client.screenshot("D:/anonym/twilio_login_ready.png")
        print("[+] Screenshot: D:/anonym/twilio_login_ready.png")
        
        # 6. Submit
        print("[6] Submitting login form...")
        client.click('input[type="password"]')
        time.sleep(0.5)
        client.press_key("Enter")
        time.sleep(1)
        client.click('button[type="submit"]')
        
        print("[7] Waiting 12 seconds for login response...")
        time.sleep(12)
        
        client.screenshot("D:/anonym/twilio_post_login.png")
        print("[+] Screenshot: D:/anonym/twilio_post_login.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER LOGIN ---")
        print(content[:1500])
        print("---------------------------")
        
        # 7. Check if 2FA / OTP screen is shown
        if "verification" in content.lower() or "code" in content.lower() or "sms" in content.lower():
            print("[8] 2FA detected! Polling ADB for SMS OTP...")
            otp = None
            for attempt in range(10):
                otp = fetch_sms_otp()
                if otp:
                    print(f"  [+] Found SMS OTP via ADB: {otp}")
                    break
                time.sleep(3)
                
            if otp:
                print(f"[9] Entering OTP: {otp} ...")
                client.fill('input[type="text"]', otp)
                time.sleep(1)
                client.press_key("Enter")
                time.sleep(8)
                client.screenshot("D:/anonym/twilio_post_otp.png")
                print("[+] Screenshot: D:/anonym/twilio_post_otp.png")
                print(client.get_content()[:1500])
                
    except Exception as e:
        print("Error during final login:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
