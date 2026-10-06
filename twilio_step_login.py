import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("=" * 60)
    print("TWILIO LOGIN: SUBMIT PASSWORD & HANDLE AUTH")
    print("=" * 60)
    
    client = Agent360Client()
    client.start()
    
    try:
        tabs = client.list_tabs()
        print("Open tabs:")
        twilio_tab = None
        for t in tabs:
            print(f"  Tab {t.get('id')}: {t.get('url')} | {t.get('title')}")
            if "twilio.com" in t.get("url", ""):
                twilio_tab = t
        
        if twilio_tab:
            print(f"Switching to Twilio tab: {twilio_tab.get('id')}")
            client.switch_tab(twilio_tab.get('id'))
            time.sleep(2)
        else:
            print("No Twilio tab found, navigating to login.twilio.com/u/login ...")
            client.navigate("https://login.twilio.com/u/login")
            time.sleep(4)
            client.fill("#email", "isearch.xsolve@gmail.com")
            time.sleep(1)
            client.click("#email-next")
            time.sleep(5)

        # Check page content
        content = client.get_content()
        print("Page Content Summary:")
        print(content[:800])

        # Find password field and fill
        print("\nAttempting to fill password...")
        # Inspect input elements
        res = client.execute_script("""
            () => {
                const pw = document.querySelector('input[type="password"]') || document.querySelector('#password');
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]');
                return {
                    hasPassword: !!pw,
                    pwId: pw ? pw.id : null,
                    pwName: pw ? pw.name : null,
                    hasBtn: !!btn,
                    btnId: btn ? btn.id : null,
                    btnText: btn ? btn.innerText : null
                };
            }
        """)
        print("Script check for form:", res)

        # Fill password
        pw_selector = "#password"
        print(f"Filling password via {pw_selector}...")
        fill_res = client.fill(pw_selector, "KiloBaba2026!#Wire")
        print("Password fill res:", fill_res)
        time.sleep(1)

        # Click submit
        print("Clicking submit button...")
        click_res = client.click('button[type="submit"]')
        print("Click res:", click_res)

        # Wait 8 seconds
        print("Waiting 8 seconds for login response...")
        time.sleep(8)

        client.screenshot(r"D:\anonym\twilio_login_after_submit.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_login_after_submit.png")

        content2 = client.get_content()
        print("\n--- PAGE CONTENT AFTER PASSWORD SUBMISSION ---")
        print(content2[:1500])
        print("----------------------------------------------")

    except Exception as e:
        print("Error during login execution:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
