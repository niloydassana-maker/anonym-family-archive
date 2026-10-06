import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def eval_js(client, code):
    # Ensure code is an IIFE if it starts with () =>
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
    print("TWILIO WWW.TWILIO.COM/LOGIN FLOW")
    print("=" * 60)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[0] Navigating to https://www.twilio.com/login ...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(5)

        # Check current inputs on page
        info = eval_js(client, """
            () => {
                const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
                    id: i.id,
                    name: i.name,
                    type: i.type,
                    placeholder: i.placeholder,
                    value: i.value
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
        print("Initial Page State:")
        print(json.dumps(info, indent=2))
        
        # If we are on the email input page:
        print("\n[1] Filling email address...")
        fill_res = client.fill("input", "isearch.xsolve@gmail.com")
        print("Fill res:", fill_res)
        time.sleep(1)
        
        # Click Continue
        print("\n[2] Clicking Continue button...")
        click_res = client.click("button")
        print("Click res:", click_res)
        
        print("\n[3] Waiting 6 seconds for password / next screen...")
        time.sleep(6)
        
        client.screenshot("D:/anonym/twilio_www_after_continue.png")
        print("[+] Screenshot saved to D:/anonym/twilio_www_after_continue.png")
        
        content = client.get_content()
        print("\n--- CONTENT AFTER CONTINUE ---")
        print(content[:1500])
        print("------------------------------")
        
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
