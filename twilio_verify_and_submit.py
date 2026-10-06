import sys
import os
import time
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("Connecting to Agent360...", flush=True)
    client = Agent360Client()
    client.start()
    
    try:
        print("Navigating to https://auth.twilio.com/auth0/email-verification ...", flush=True)
        nav_res = client.navigate("https://auth.twilio.com/auth0/email-verification")
        print("Nav result:", json.dumps(nav_res, ensure_ascii=True))
        time.sleep(5)
        
        screenshot_path = r"D:\anonym\twilio_verify_page.png"
        client.screenshot(screenshot_path)
        print("Captured screenshot to:", screenshot_path)
        
        # Check inputs and text
        script = """
        (function() {
            var inputs = Array.from(document.querySelectorAll('input, button')).map(function(el) {
                return {
                    tag: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    text: (el.innerText || el.value || '').trim()
                };
            });
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                body: document.body.innerText.slice(0, 500),
                elements: inputs
            });
        })()
        """
        page_info = client.call_tool("browser_execute_script", {"script": script})
        print("Page info:", json.dumps(page_info, ensure_ascii=True))
        
        CODE = "P33XA2"
        fill_code_script = f"""
        (function() {{
            var input = document.querySelector('input[type="text"]') || document.querySelector('input');
            if (!input) return 'Input not found';
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(input, '{CODE}');
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Code filled successfully into ' + (input.id || input.name || 'input');
        }})()
        """
        fill_res = client.call_tool("browser_execute_script", {"script": fill_code_script})
        print("Fill result:", json.dumps(fill_res, ensure_ascii=True))
        time.sleep(1)
        
        click_btn_script = """
        (function() {
            var btn = document.querySelector('button[type="submit"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Continue'));
            if (btn) {
                btn.click();
                return 'Clicked button: ' + btn.innerText;
            }
            return 'Button not found';
        })()
        """
        click_res = client.call_tool("browser_execute_script", {"script": click_btn_script})
        print("Click result:", json.dumps(click_res, ensure_ascii=True))
        
        time.sleep(6)
        
        client.screenshot(r"D:\anonym\twilio_after_email_submit.png")
        print("Captured D:\anonym\twilio_after_email_submit.png")
        
        state_script = """
        (function() {
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                body: document.body.innerText.slice(0, 500)
            });
        })()
        """
        state_res = client.call_tool("browser_execute_script", {"script": state_script})
        print("Next page state:", json.dumps(state_res, ensure_ascii=True))
        
    except Exception as e:
        print("Error during execution:", repr(e))
    finally:
        client.close()
        print("Client closed.")

if __name__ == "__main__":
    main()
