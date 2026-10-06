import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("=" * 60, flush=True)
    print("TWILIO REGISTRATION: NAVIGATE + FILL + SUBMIT", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    print("[+] Agent360 Client started.", flush=True)
    
    try:
        print("[1] Navigating to Twilio signup page...", flush=True)
        nav_res = client.navigate("https://www.twilio.com/try-twilio")
        print("  Navigated:", nav_res, flush=True)
        time.sleep(5)
        
        # Fill form via direct DOM script
        fill_script = """
        (function() {
            function setInput(id, val) {
                var el = document.getElementById(id);
                if (el) {
                    el.focus();
                    el.value = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            }
            
            var r1 = setInput('first-name', 'Kunal');
            var r2 = setInput('last-name', 'Das');
            var r3 = setInput('email', 'isearch.xsolve@gmail.com');
            var r4 = setInput('password', 'KiloBaba2026!#Wire');
            
            var terms = document.getElementById('terms-of-service');
            if (terms && !terms.checked) {
                terms.click();
            }
            
            return JSON.stringify({
                firstName: r1,
                lastName: r2,
                email: r3,
                password: r4,
                termsChecked: terms ? terms.checked : false
            });
        })()
        """
        print("[2] Filling form fields...", flush=True)
        fill_res = client.call_tool("browser_execute_script", {"script": fill_script})
        print("  Fill result:", fill_res, flush=True)
        time.sleep(2)
        
        # Screenshot filled form
        client.screenshot(r"D:\anonym\twilio_step2_filled.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_step2_filled.png", flush=True)
        
        # Click Continue button
        print("[3] Clicking Continue button...", flush=True)
        click_script = """
        (function() {
            var btn = document.querySelector('button[type="submit"][name="action"]');
            if (btn) {
                btn.click();
                return 'CLICKED_CONTINUE';
            }
            return 'BTN_NOT_FOUND';
        })()
        """
        click_res = client.call_tool("browser_execute_script", {"script": click_script})
        print("  Click result:", click_res, flush=True)
        
        # Wait 8 seconds for page response
        print("[4] Waiting 8 seconds for response...", flush=True)
        time.sleep(8)
        
        # Screenshot submitted result
        client.screenshot(r"D:\anonym\twilio_step3_submitted.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_step3_submitted.png", flush=True)
        
        # Get new content
        content = client.get_content()
        print(f"[5] Result page content ({len(content)} chars):", flush=True)
        print("--- CONTENT ---", flush=True)
        print(content[:1500], flush=True)
        print("---------------", flush=True)

    except Exception as e:
        print("Error during Agent360 submit:", e, flush=True)
    finally:
        client.close()
        print("[*] Agent360 client closed.", flush=True)

if __name__ == "__main__":
    main()
