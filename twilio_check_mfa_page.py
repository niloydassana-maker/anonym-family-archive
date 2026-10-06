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
        # Wait a few seconds for MFA page to settle
        time.sleep(3)
        client.screenshot(r"D:\anonym\twilio_reg_step5_loaded.png")
        print("Captured screenshot to D:\anonym\twilio_reg_step5_loaded.png")
        
        script = """
        (function() {
            var inputs = Array.from(document.querySelectorAll('input, button, select, a')).map(function(el) {
                return {
                    tag: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    text: (el.innerText || el.value || '').trim().slice(0, 80),
                    ariaLabel: el.getAttribute('aria-label') || ''
                };
            });
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                body: document.body.innerText.slice(0, 600),
                elements: inputs
            });
        })()
        """
        page_info = client.call_tool("browser_execute_script", {"script": script})
        print("MFA Page info:", json.dumps(page_info, ensure_ascii=True))
        
    except Exception as e:
        print("Error during execution:", repr(e))
    finally:
        client.close()
        print("Client closed.")

if __name__ == "__main__":
    main()
