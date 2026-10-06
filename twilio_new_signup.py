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
        print("Navigating to https://www.twilio.com/try-twilio ...", flush=True)
        nav_res = client.navigate("https://www.twilio.com/try-twilio")
        print("Nav result:", nav_res, flush=True)
        time.sleep(6)
        
        screenshot_path = r"D:\anonym\twilio_new_signup_step1.png"
        client.screenshot(screenshot_path)
        print("Captured screenshot to:", screenshot_path, flush=True)
        
        # Check inputs
        script = """
        (function() {
            var inputs = Array.from(document.querySelectorAll('input, button, a')).map(function(el) {
                return {
                    tag: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    text: (el.innerText || el.value || '').trim().slice(0, 50),
                    ariaLabel: el.getAttribute('aria-label') || ''
                };
            });
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                elements: inputs
            });
        })()
        """
        res = client.call_tool("browser_execute_script", {"script": script})
        print("Page info:", res, flush=True)
        
    except Exception as e:
        print("Error during execution:", e, flush=True)
    finally:
        client.close()
        print("Client closed.", flush=True)

if __name__ == "__main__":
    main()
