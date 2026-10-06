import sys
import os
import time

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("=" * 60)
    print("SUBMITTING TWILIO WITH SAVED PASSWORD: Ku3104123!@#456$%")
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
            print("Navigating to login.twilio.com/u/login ...")
            client.navigate("https://login.twilio.com/u/login")
            time.sleep(4)
            client.fill("#email", "isearch.xsolve@gmail.com")
            time.sleep(1)
            client.click("#email-next")
            time.sleep(4)

        content = client.get_content()
        print("Initial content summary:", content[:300])
        
        # We can use execute_script to set the value cleanly using React's value setter and submit the form!
        submit_script = """
        () => {
            const form = document.querySelector('form');
            const pwInput = document.querySelector('input[type="password"]');
            const submitBtn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]');
            
            // Set password properly triggering React events
            if (pwInput) {
                // native setter so React detects the change
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(pwInput, "Ku3104123!@#456$%");
                pwInput.dispatchEvent(new Event('input', { bubbles: true }));
                pwInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            // Now click submit button or requestSubmit on form
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.click();
                return { success: true, method: 'btn.click', formFound: !!form };
            } else if (form) {
                form.requestSubmit();
                return { success: true, method: 'form.requestSubmit' };
            }
            return { success: false, reason: 'no button or form found' };
        }
        """
        
        res = client.execute_script(submit_script)
        print("Script execution result:", res)
        
        print("Waiting 10 seconds for response...")
        time.sleep(10)
        
        client.screenshot(r"D:\anonym\twilio_login_saved_pw_result.png")
        print("[+] Screenshot saved to D:\\anonym\\twilio_login_saved_pw_result.png")
        
        content2 = client.get_content()
        print("\n--- PAGE CONTENT AFTER SUBMISSION ---")
        print(content2[:1500])
        print("-------------------------------------")

    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
