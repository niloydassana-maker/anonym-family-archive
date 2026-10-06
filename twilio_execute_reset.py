import sys
import os
import time
import json
import subprocess

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

RESET_URL = "https://links.twiliocdn.com/ls/click?upn=u001.s8B7Bdj-2BO6qOEbA-2BPKse2XjCDlB0aVVAhqI0wpiHwMUdzKV92RYfJSNxheq3DKkp6x1LTVnoFxEkRCoLKKIrkTwa5HPLeADbFUnAdz8nWJwt0eczhJAyLC-2B3ibmsLXUfNb3r_0AmqDpppvmSRS1kHpboorl6l69LxSoSMRXUo8p-2FNXnc9s3iwIXq2ip9OMX88-2FaiIS6ujpHCJVUgYUH-2FudlTgGYY-2Fi8n70jqpTZMR8I82fdYwN6CJ3qh1hWl04vPxKencB-2B3Km3MojxOKdhZfl3L4hn4-2BsjEsMkgAO0Xqr9NwsZk9KAGbD-2BBIyVUy8BlLtBl-2B5OMRzwQn7RRz-2BkH4z2A8gw-3D-3D"
NEW_PASSWORD = "KiloBaba2026!#Wire"

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
    print("TWILIO: NAVIGATE TO RESET LINK & SET NEW PASSWORD")
    print("=" * 60)
    
    # 1. Bring Chrome to front
    ps_cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('Chrome')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to Twilio Password Reset Link...")
        client.navigate(RESET_URL)
        time.sleep(6)
        
        client.screenshot("D:/anonym/twilio_reset_page_loaded.png")
        print("[+] Screenshot saved: D:/anonym/twilio_reset_page_loaded.png")
        
        # 2. Inspect the password fields
        info = eval_js(client, """
            () => {
                const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
                    id: i.id,
                    name: i.name,
                    type: i.type,
                    placeholder: i.placeholder
                }));
                const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                    id: b.id,
                    text: b.innerText
                }));
                return {
                    url: window.location.href,
                    inputs,
                    buttons
                };
            }
        """)
        print("[2] Reset Page Form Elements:")
        print(json.dumps(info, indent=2))
        
        # 3. Fill new password and confirm password
        print(f"[3] Setting new password: {NEW_PASSWORD} ...")
        fill_res = eval_js(client, f"""
            () => {{
                const pwInputs = document.querySelectorAll('input[type="password"]');
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                pwInputs.forEach(i => {{
                    nativeSetter.call(i, "{NEW_PASSWORD}");
                    i.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    i.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }});
                return {{ count: pwInputs.length }};
            }}
        """)
        print("Fill result:", fill_res)
        time.sleep(2)
        
        # Also try direct client.fill for known selectors if any
        inputs_list = info.get('result', {}).get('inputs', []) if isinstance(info, dict) else []
        for inp in inputs_list:
            if inp.get('type') == 'password' and inp.get('id'):
                print(f"Direct fill #{inp['id']}...")
                client.fill(f"#{inp['id']}", NEW_PASSWORD)
                time.sleep(0.5)
                
        client.screenshot("D:/anonym/twilio_reset_filled.png")
        print("[+] Screenshot: D:/anonym/twilio_reset_filled.png")
        
        # 4. Submit form
        print("[4] Submitting new password...")
        client.click('button[type="submit"]')
        time.sleep(1)
        client.press_key("Enter")
        
        print("[5] Waiting 12 seconds for reset completion & redirect...")
        time.sleep(12)
        
        client.screenshot("D:/anonym/twilio_after_new_password_set.png")
        print("[+] Screenshot: D:/anonym/twilio_after_new_password_set.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER PASSWORD RESET ---")
        print(content[:2500])
        print("------------------------------------")
        
    except Exception as e:
        print("Error during reset execution:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
