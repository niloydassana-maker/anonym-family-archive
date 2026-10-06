import sys
import os
import time
import json
import subprocess

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

ADB = r"D:\anonym\platform-tools\adb.exe"
NOKIA_ID = "G2866620341C0402558"
IQOO_ID = "10BE8135QM001KK"

EMAIL = "isearch.xsolve@gmail.com"
PASSWORD = "KiloBaba2026!#Wire"
FIRST_NAME = "Kunal"
LAST_NAME = "Das"

def get_latest_sms(device_id):
    cmd = [ADB, "-s", device_id, "shell", "content", "query", "--uri", "content://sms/inbox", "--projection", "address:body:date"]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    lines = res.stdout.strip().splitlines()
    if lines:
        return lines[-1]
    return ""

def main():
    print("=" * 60, flush=True)
    print("TWILIO REGISTRATION VIA AGENT360 (CHROME PROFILE 17)", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    print("[1] Starting Agent360 Client...", flush=True)
    client.start()
    print("[+] Agent360 Client connected to real Chrome extension!", flush=True)
    
    try:
        print("[2] Navigating to https://www.twilio.com/try-twilio ...", flush=True)
        nav_res = client.navigate("https://www.twilio.com/try-twilio")
        print("  Nav result:", nav_res, flush=True)
        time.sleep(5)
        
        # Take initial screenshot
        print("[3] Capturing initial page screenshot...", flush=True)
        client.screenshot(r"D:\anonym\twilio_step1_nav.png")
        
        # Get content
        content = client.get_content()
        print(f"[4] Page loaded. Content length: {len(content)} characters.", flush=True)
        print("--- CONTENT PREVIEW ---", flush=True)
        print(content[:800], flush=True)
        print("-----------------------", flush=True)

        # Let's inspect fields using execute_script
        print("[5] Inspecting form inputs on page...", flush=True)
        inspect_script = """
        (function() {
            var inputs = Array.from(document.querySelectorAll('input, button, a')).map(function(el) {
                return {
                    tag: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    text: el.innerText || el.value || '',
                    ariaLabel: el.getAttribute('aria-label') || ''
                };
            });
            return JSON.stringify(inputs);
        })()
        """
        eval_res = client.call_tool("browser_execute_script", {"script": inspect_script})
        print("Inputs on page:", eval_res, flush=True)

    except Exception as e:
        print("Error during Agent360 execution:", e, flush=True)
    finally:
        client.close()
        print("[*] Agent360 client closed.", flush=True)

if __name__ == "__main__":
    main()
