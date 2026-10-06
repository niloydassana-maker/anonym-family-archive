import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("=" * 60, flush=True)
    print("TWILIO LOGIN: NAVIGATE + ENTER EMAIL + CHECK RESULT", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    print("[+] Agent360 Client started.", flush=True)
    
    try:
        print("[1] Navigating to https://login.twilio.com/u/login ...", flush=True)
        nav_res = client.navigate("https://login.twilio.com/u/login")
        print("  Navigated:", nav_res, flush=True)
        time.sleep(4)
        
        # Enter email and click email-next
        print("[2] Entering email isearch.xsolve@gmail.com ...", flush=True)
        enter_script = """
        (function() {
            var el = document.getElementById('email');
            if (el) {
                el.focus();
                el.value = 'isearch.xsolve@gmail.com';
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                
                var btn = document.getElementById('email-next');
                if (btn) {
                    btn.click();
                    return 'EMAIL_ENTERED_AND_CLICKED';
                }
                return 'BTN_NOT_FOUND';
            }
            return 'EMAIL_NOT_FOUND';
        })()
        """
        res = client.call_tool("browser_execute_script", {"script": enter_script})
        print("  Action result:", res, flush=True)
        
        # Wait 6 seconds
        print("[3] Waiting 6 seconds for response...", flush=True)
        time.sleep(6)
        
        client.screenshot(r"D:\anonym\twilio_login_step2_result.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_login_step2_result.png", flush=True)
        
        content = client.get_content()
        print("--- CONTENT AFTER EMAIL SUBMIT ---", flush=True)
        print(content[:1500], flush=True)
        print("----------------------------------", flush=True)
        
        # Inspect what is asked next (password, Google auth, OTP, etc.)
        inspect_script = """
        (function() {
            return JSON.stringify(Array.from(document.querySelectorAll('input, button, a')).map(function(el) {
                return {
                    tag: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    text: el.innerText || el.value || '',
                    ariaLabel: el.getAttribute('aria-label') || ''
                };
            }));
        })()
        """
        next_items = client.call_tool("browser_execute_script", {"script": inspect_script})
        print("Next page elements:", next_items, flush=True)

    except Exception as e:
        print("Error during login step 2:", e, flush=True)
    finally:
        client.close()
        print("[*] Agent360 client closed.", flush=True)

if __name__ == "__main__":
    main()
