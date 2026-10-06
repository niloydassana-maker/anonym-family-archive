import sys
import os
import time
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    PHONE = "9830739230"
    print(f"Connecting to Agent360 to submit phone number: {PHONE}...", flush=True)
    client = Agent360Client()
    client.start()
    
    try:
        fill_script = f"""
        (function() {{
            var input = document.querySelector('#phone-input') || document.querySelector('input[type="tel"]');
            if (!input) return 'Phone input not found';
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(input, '{PHONE}');
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Phone filled: ' + input.value;
        }})()
        """
        fill_res = client.call_tool("browser_execute_script", {"script": fill_script})
        print("Fill result:", json.dumps(fill_res, ensure_ascii=True))
        time.sleep(1)
        
        client.screenshot(r"D:\anonym\twilio_phone_filled.png")
        
        print("Clicking 'Send code via SMS' button...")
        click_script = """
        (function() {
            var btn = document.querySelector('#send-sms-btn') || document.querySelector('button[type="submit"]');
            if (btn) {
                btn.click();
                return 'Clicked button: ' + btn.innerText;
            }
            return 'Button not found';
        })()
        """
        click_res = client.call_tool("browser_execute_script", {"script": click_script})
        print("Click result:", json.dumps(click_res, ensure_ascii=True))
        
        time.sleep(5)
        
        client.screenshot(r"D:\anonym\twilio_sms_code_sent.png")
        print("Captured D:\anonym\twilio_sms_code_sent.png")
        
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
        print("Page state after SMS trigger:", json.dumps(state_res, ensure_ascii=True))
        
    except Exception as e:
        print("Error during execution:", repr(e))
    finally:
        client.close()
        print("Client closed.")

if __name__ == "__main__":
    main()
