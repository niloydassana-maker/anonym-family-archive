import sys
import os
import time
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    EMAIL = "isearch.xsolve+backup@gmail.com"
    PASSWORD = "KiloBaba2026!#Wire"
    PHONE = "9830739230"
    
    print("=" * 60, flush=True)
    print(f"LOGGING IN TO BACKUP TWILIO ACCOUNT {EMAIL} & TRIGGERING SMS TO {PHONE}", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://login.twilio.com/u/login ...", flush=True)
        nav_res = client.navigate("https://login.twilio.com/u/login")
        print("Nav result:", json.dumps(nav_res, ensure_ascii=True))
        time.sleep(5)
        
        client.screenshot(r"D:\anonym\twilio_login_step1.png")
        
        print(f"[2] Entering email: {EMAIL}...", flush=True)
        fill_email_script = f"""
        (function() {{
            var el = document.querySelector('#email') || document.querySelector('input[type="email"]') || document.querySelector('input');
            if (!el) return 'Email input not found';
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(el, '{EMAIL}');
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Email filled: ' + el.value;
        }})()
        """
        res_email = client.call_tool("browser_execute_script", {"script": fill_email_script})
        print("Email fill result:", json.dumps(res_email, ensure_ascii=True))
        time.sleep(1)
        
        print("[3] Clicking Continue...", flush=True)
        click_cont_script = """
        (function() {
            var btn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Continue'));
            if (btn) {
                btn.click();
                return 'Clicked continue';
            }
            return 'Button not found';
        })()
        """
        res_cont = client.call_tool("browser_execute_script", {"script": click_cont_script})
        print("Continue click result:", json.dumps(res_cont, ensure_ascii=True))
        time.sleep(4)
        
        client.screenshot(r"D:\anonym\twilio_login_step2_pw.png")
        
        print("[4] Entering password...", flush=True)
        fill_pw_script = f"""
        (function() {{
            var el = document.querySelector('input[type="password"]');
            if (!el) return 'Password input not found';
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(el, '{PASSWORD}');
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Password filled';
        }})()
        """
        res_pw = client.call_tool("browser_execute_script", {"script": fill_pw_script})
        print("Password fill result:", json.dumps(res_pw, ensure_ascii=True))
        time.sleep(1)
        
        print("[5] Clicking Log In...", flush=True)
        click_login_script = """
        (function() {
            var btn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Log In') || b.innerText.includes('Continue'));
            if (btn) {
                btn.click();
                return 'Clicked Log In';
            }
            return 'Button not found';
        })()
        """
        res_login = client.call_tool("browser_execute_script", {"script": click_login_script})
        print("Log In click result:", json.dumps(res_login, ensure_ascii=True))
        time.sleep(6)
        
        client.screenshot(r"D:\anonym\twilio_login_step3_after_login.png")
        
        # Check current screen
        check_script = """
        (function() {
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                body: document.body.innerText.slice(0, 500)
            });
        })()
        """
        screen_info = client.call_tool("browser_execute_script", {"script": check_script})
        print("Screen after login:", json.dumps(screen_info, ensure_ascii=True))
        
        print(f"[6] Filling phone number: {PHONE}...", flush=True)
        fill_phone_script = f"""
        (function() {{
            var el = document.querySelector('#phone-input') || document.querySelector('input[type="tel"]') || document.querySelector('input');
            if (!el) return 'Phone input not found';
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(el, '{PHONE}');
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Phone filled: ' + el.value;
        }})()
        """
        res_phone = client.call_tool("browser_execute_script", {"script": fill_phone_script})
        print("Phone fill result:", json.dumps(res_phone, ensure_ascii=True))
        time.sleep(1)
        
        print("[7] Clicking 'Send code via SMS'...", flush=True)
        click_sms_script = """
        (function() {
            var btn = document.querySelector('#send-sms-btn') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Send code via SMS') || b.innerText.includes('SMS'));
            if (btn) {
                btn.click();
                return 'Clicked send SMS button: ' + btn.innerText;
            }
            return 'Send SMS button not found';
        })()
        """
        res_sms = client.call_tool("browser_execute_script", {"script": click_sms_script})
        print("Send SMS result:", json.dumps(res_sms, ensure_ascii=True))
        time.sleep(5)
        
        client.screenshot(r"D:\anonym\twilio_backup_sms_sent.png")
        final_screen = client.call_tool("browser_execute_script", {"script": check_script})
        print("Final screen status:", json.dumps(final_screen, ensure_ascii=True))
        
    except Exception as e:
        print("Error during execution:", repr(e))
    finally:
        client.close()
        print("Client closed.")

if __name__ == "__main__":
    main()
