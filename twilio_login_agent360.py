import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("=" * 60, flush=True)
    print("TWILIO LOGIN VIA AGENT360 (isearch.xsolve@gmail.com)", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    print("[+] Agent360 Client started.", flush=True)
    
    try:
        print("[1] Navigating to https://login.twilio.com/u/login ...", flush=True)
        nav_res = client.navigate("https://login.twilio.com/u/login")
        print("  Navigated:", nav_res, flush=True)
        time.sleep(5)
        
        # Screenshot login page
        client.screenshot(r"D:\anonym\twilio_login_step1.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_login_step1.png", flush=True)
        
        # Get content & inspect buttons/inputs
        content = client.get_content()
        print("--- LOGIN PAGE CONTENT ---", flush=True)
        print(content[:1000], flush=True)
        print("--------------------------", flush=True)
        
        inspect_script = """
        (function() {
            var items = Array.from(document.querySelectorAll('input, button, a')).map(function(el) {
                return {
                    tag: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    text: el.innerText || el.value || '',
                    href: el.href || ''
                };
            });
            return JSON.stringify(items);
        })()
        """
        items_res = client.call_tool("browser_execute_script", {"script": inspect_script})
        print("Interactive elements:", items_res, flush=True)

    except Exception as e:
        print("Error during login probe:", e, flush=True)
    finally:
        client.close()
        print("[*] Agent360 client closed.", flush=True)

if __name__ == "__main__":
    main()
