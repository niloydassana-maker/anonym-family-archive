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
    print("ONE-SHOT CONTINUOUS TWILIO LOGIN FLOW")
    print("=" * 60)
    
    # 1. Bring Chrome to front
    ps_cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('Chrome')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)
    
    client = Agent360Client()
    client.start()
    
    try:
        # 2. Navigate to login
        print("[1] Navigating to https://www.twilio.com/login ...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(5)
        
        # 3. Fill email
        print("[2] Filling email...")
        client.fill("#email", "isearch.xsolve@gmail.com")
        time.sleep(1)
        
        # 4. Click Continue
        print("[3] Clicking #email-next...")
        client.click("#email-next")
        time.sleep(6)
        
        # 5. Check if password input is present
        state = eval_js(client, """
            () => {
                const pw = document.querySelector('input[type="password"]');
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]');
                return {
                    url: window.location.href,
                    hasPw: !!pw,
                    pwLen: pw ? pw.value.length : 0,
                    hasBtn: !!btn,
                    btnText: btn ? btn.innerText : null
                };
            }
        """)
        print("[4] Password screen state:", state)
        
        # 6. Fill password if not filled
        pw_len = state.get('result', {}).get('pwLen', 0) if isinstance(state, dict) else 0
        if pw_len == 0:
            print("[5] Setting password...")
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
        else:
            print(f"[5] Password already filled with {pw_len} characters from Chrome autofill.")
            
        # 7. Wait 5s for Turnstile
        print("[6] Waiting 5s for Turnstile to settle...")
        time.sleep(5)
        
        client.screenshot("D:/anonym/twilio_step_ready_to_submit.png")
        print("[+] Screenshot saved: D:/anonym/twilio_step_ready_to_submit.png")
        
        # 8. Submit via click and Enter key
        print("[7] Submitting password...")
        # First try clicking button
        client.click('button[type="submit"]')
        time.sleep(1)
        # Also press Enter key as backup
        client.press_key("Enter")
        
        print("[8] Waiting 12 seconds for login redirect / verification...")
        time.sleep(12)
        
        client.screenshot("D:/anonym/twilio_step_submitted_result.png")
        print("[+] Screenshot saved: D:/anonym/twilio_step_submitted_result.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER LOGIN SUBMISSION ---")
        print(content[:2000])
        print("--------------------------------------")
        
    except Exception as e:
        print("Error during continuous login:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
