import sys
import os
import time
import json
import subprocess

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

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

def main():
    print("=" * 60)
    print("TWILIO LOGIN: PERFECT STATE-DRIVEN SEQUENCE")
    print("=" * 60)
    
    # 1. Bring Chrome to front
    print("[1] Bringing Chrome to front...")
    ps_cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('Chrome')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[2] Navigating to https://www.twilio.com/login ...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(4)
        
        print("[3] Filling email isearch.xsolve@gmail.com ...")
        client.fill("#email", "isearch.xsolve@gmail.com")
        time.sleep(1)
        
        print("[4] Clicking Continue button...")
        client.click("#email-next")
        
        # 5. Wait up to 15s for transition to login.twilio.com/u/login
        print("[5] Waiting for password screen (login.twilio.com/u/login)...")
        pw_screen_ready = False
        for i in range(15):
            url_res = eval_js(client, "() => window.location.href")
            url = ""
            if isinstance(url_res, dict):
                url = url_res.get('result', '')
            elif isinstance(url_res, str):
                url = url_res
            print(f"  Check {i+1}: URL = {url[:60]}")
            if "login.twilio.com/u/login" in str(url):
                pw_screen_ready = True
                break
            time.sleep(1)
            
        if not pw_screen_ready:
            print("Warning: Did not see login.twilio.com/u/login within 15s, continuing anyway...")
            
        print("[6] Giving 5 seconds for password autofill & Turnstile...")
        time.sleep(5)
        
        # Re-activate Chrome to ensure window focus
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        time.sleep(1)
        
        # Check password input
        pw_check = eval_js(client, """
            () => {
                const pw = document.querySelector('input[type="password"]');
                return {
                    found: !!pw,
                    length: pw ? pw.value.length : 0
                };
            }
        """)
        print("Password field status:", pw_check)
        
        # If empty, set saved password
        if isinstance(pw_check, dict) and pw_check.get('result', {}).get('length', 0) == 0:
            print("Field was empty, setting Ku3104123!@#456$%...")
            eval_js(client, """
                () => {
                    const pw = document.querySelector('input[type="password"]');
                    if (pw) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        nativeSetter.call(pw, "Ku3104123!@#456$%");
                        pw.dispatchEvent(new Event('input', { bubbles: true }));
                        pw.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """)
            time.sleep(1)
            
        # Take screenshot before submit
        client.screenshot("D:/anonym/twilio_perfect_before_submit.png")
        print("[+] Screenshot: D:/anonym/twilio_perfect_before_submit.png")
        
        # Submit by clicking password field and pressing Enter
        print("[7] Submitting form via Enter key & submit click...")
        client.click('input[type="password"]')
        time.sleep(0.5)
        client.press_key("Enter")
        time.sleep(1)
        client.click('button[type="submit"]')
        
        print("[8] Waiting 15 seconds for console redirect / 2FA screen...")
        time.sleep(15)
        
        client.screenshot("D:/anonym/twilio_perfect_after_submit.png")
        print("[+] Screenshot: D:/anonym/twilio_perfect_after_submit.png")
        
        final_url = eval_js(client, "() => window.location.href")
        print("\nFinal URL:", final_url)
        
        content = client.get_content()
        print("\n--- PAGE CONTENT ---")
        print(content[:2500])
        print("--------------------")

    except Exception as e:
        print("Error during perfect login:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
