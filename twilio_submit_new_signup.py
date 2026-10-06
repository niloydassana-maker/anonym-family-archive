import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("Connecting to Agent360...", flush=True)
    client = Agent360Client()
    client.start()
    
    try:
        EMAIL = "isearch.xsolve+demo@gmail.com"
        PASSWORD = "KiloBaba2026!#Wire"
        FIRST = "Kunal"
        LAST = "Das"
        
        print("Navigating to https://www.twilio.com/try-twilio ...", flush=True)
        nav_res = client.navigate("https://www.twilio.com/try-twilio")
        print("Nav result:", nav_res, flush=True)
        time.sleep(6)
        
        print(f"Filling signup form for {EMAIL}...", flush=True)
        
        # Use native setters via execute_script to ensure React/form state updates properly
        fill_script = f"""
        (function() {{
            function setVal(selector, val) {{
                var el = document.querySelector(selector);
                if (!el) return 'Not found: ' + selector;
                var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(el, val);
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'Filled: ' + selector;
            }}
            
            var r1 = setVal('#first-name', '{FIRST}');
            var r2 = setVal('#last-name', '{LAST}');
            var r3 = setVal('#email', '{EMAIL}');
            var r4 = setVal('#password', '{PASSWORD}');
            
            var tos = document.querySelector('#terms-of-service');
            if (tos && !tos.checked) {{
                tos.click();
            }}
            
            return JSON.stringify({{ r1, r2, r3, r4, tos: tos ? tos.checked : false }});
        }})()
        """
        
        res = client.call_tool("browser_execute_script", {"script": fill_script})
        print("Fill result:", res, flush=True)
        time.sleep(2)
        
        screenshot_before = r"D:\anonym\twilio_new_signup_filled.png"
        client.screenshot(screenshot_before)
        print("Captured filled screenshot to:", screenshot_before, flush=True)
        
        print("Clicking Continue button...", flush=True)
        click_script = """
        (function() {
            var btn = document.querySelector('button[name="action"]') || document.querySelector('button[type="submit"]');
            if (btn) {
                btn.click();
                return 'Clicked ' + btn.innerText;
            }
            return 'Button not found';
        })()
        """
        click_res = client.call_tool("browser_execute_script", {"script": click_script})
        print("Click result:", click_res, flush=True)
        
        time.sleep(6)
        
        screenshot_after = r"D:\anonym\twilio_new_signup_after_submit.png"
        client.screenshot(screenshot_after)
        print("Captured after-submit screenshot to:", screenshot_after, flush=True)
        
        # Get current url and text
        info_script = """
        (function() {
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                bodyText: document.body.innerText.slice(0, 500)
            });
        })()
        """
        info_res = client.call_tool("browser_execute_script", {"script": info_script})
        print("After submit page info:", info_res, flush=True)
        
    except Exception as e:
        print("Error during execution:", e, flush=True)
    finally:
        client.close()
        print("Client closed.", flush=True)

if __name__ == "__main__":
    main()
