import sys
import os
import time
import json
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

def main():
    print("=" * 60)
    print("TWILIO LOGIN: PRECISE COORDINATES (557, 445) + SCROLL SUBMIT")
    print("=" * 60)
    
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
        
        # Wait for login.twilio.com/u/login
        print("[3] Waiting for password screen...")
        for i in range(12):
            url_res = eval_js(client, "() => window.location.href")
            url = url_res.get('result', '') if isinstance(url_res, dict) else str(url_res)
            if "login.twilio.com/u/login" in url:
                break
            time.sleep(1)
            
        time.sleep(4)
        
        # Fill password
        print(f"[4] Setting password {PASSWORD} ...")
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
        time.sleep(2)
        
        # Screenshot before clicking Turnstile
        client.screenshot("D:/anonym/exact_before_ts_click.png")
        print("[+] Screenshot: D:/anonym/exact_before_ts_click.png")
        
        # Click Turnstile checkbox at EXACT coordinates: x=557, y=445
        print("[5] Clicking Turnstile checkbox at (557, 445)...")
        c_res = client.call_tool('browser_click_xy', {'x': 557, 'y': 445})
        print("  Click res:", c_res)
        
        print("[6] Waiting 6 seconds for Turnstile to verify...")
        time.sleep(6)
        
        client.screenshot("D:/anonym/exact_after_ts_click.png")
        print("[+] Screenshot: D:/anonym/exact_after_ts_click.png")
        
        # Scroll down so Continue button is visible
        print("[7] Scrolling down 200px...")
        eval_js(client, "() => window.scrollBy(0, 250)")
        time.sleep(1)
        
        # Click Continue button
        print("[8] Submitting form via click('button[type=\"submit\"]') and Enter key...")
        client.click('button[type="submit"]')
        time.sleep(0.5)
        client.press_key("Enter")
        
        print("[9] Waiting 15 seconds for console redirect / 2FA...")
        time.sleep(15)
        
        client.screenshot("D:/anonym/exact_final_result.png")
        print("[+] Screenshot: D:/anonym/exact_final_result.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER SUBMIT ---")
        print(content[:2500])
        print("----------------------------")
        
    except Exception as e:
        print("Error during exact login:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
