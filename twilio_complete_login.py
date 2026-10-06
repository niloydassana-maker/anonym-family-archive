import sys
import os
import time
import json
import subprocess

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def bring_chrome_to_front():
    ps_cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('Chrome')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)

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
    print("TWILIO COMPLETE LOGIN SEQUENCE")
    print("=" * 60)
    
    # Bring Chrome to front so Cloudflare Turnstile activates
    print("[1] Bringing Chrome to front...")
    bring_chrome_to_front()
    
    client = Agent360Client()
    client.start()
    
    try:
        # Check current inputs
        info = eval_js(client, """
            () => {
                const pwInput = document.querySelector('input[type="password"]');
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button');
                const ts = document.querySelector('[name="cf-turnstile-response"]');
                return {
                    url: window.location.href,
                    pwLen: pwInput ? pwInput.value.length : 0,
                    btnText: btn ? btn.innerText : null,
                    btnDisabled: btn ? btn.disabled : null,
                    tsValueLen: ts ? (ts.value || '').length : 0
                };
            }
        """)
        print("[2] Current Page Info:", info)
        
        # If password length is 0, set it to saved password
        if isinstance(info, dict) and info.get('pwLen', 0) == 0:
            print("[3] Setting password via native setter...")
            eval_js(client, """
                () => {
                    const pwInput = document.querySelector('input[type="password"]');
                    if (pwInput) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        nativeSetter.call(pwInput, "Ku3104123!@#456$%");
                        pwInput.dispatchEvent(new Event('input', { bubbles: true }));
                        pwInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """)
            time.sleep(1)
            
        # Give Turnstile up to 8 seconds to settle
        print("[4] Waiting 5 seconds for Turnstile verification...")
        time.sleep(5)
        
        # Click Continue / Submit
        print("[5] Clicking Continue button...")
        click_res = client.click('button[type="submit"]')
        print("Click res:", click_res)
        if not click_res or (isinstance(click_res, dict) and click_res.get('isError')):
            print("Fallback to JS submit...")
            eval_js(client, """
                () => {
                    const btn = document.querySelector('button[type="submit"]') || document.querySelector('button');
                    if (btn) btn.click();
                    else {
                        const f = document.querySelector('form');
                        if (f) f.requestSubmit();
                    }
                }
            """)
            
        print("[6] Waiting 10 seconds for login redirect / next step...")
        time.sleep(10)
        
        client.screenshot("D:/anonym/twilio_logged_in_state.png")
        print("[+] Screenshot saved to D:/anonym/twilio_logged_in_state.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER LOGIN CLICK ---")
        print(content[:1500])
        print("---------------------------------")
        
    except Exception as e:
        print("Error during login:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
