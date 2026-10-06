import sys
import os
import time

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    client = Agent360Client()
    client.start()
    
    try:
        tabs = client.list_tabs()
        for t in tabs:
            if "twilio.com" in t.get("url", ""):
                client.switch_tab(t.get("id"))
                break
        
        time.sleep(2)
        
        # Check Turnstile and form status
        status = client.execute_script("""
            () => {
                const turnstile = document.querySelector('iframe[src*="turnstile"]') || document.querySelector('iframe[src*="cloudflare"]');
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]');
                const errorAlert = document.querySelector('[role="alert"]') || document.querySelector('.error-message') || document.querySelector('.c-alert');
                return {
                    url: window.location.href,
                    turnstileFound: !!turnstile,
                    btnDisabled: btn ? btn.disabled : null,
                    btnText: btn ? btn.innerText : null,
                    errorText: errorAlert ? errorAlert.innerText : null
                };
            }
        """)
        print("Page state:", status)
        
        client.screenshot(r"D:\anonym\twilio_turnstile_check.png")
        print("Saved screenshot to D:\\anonym\\twilio_turnstile_check.png")
        
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
