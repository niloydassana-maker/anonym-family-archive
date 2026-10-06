import sys
import os
import time
import json
import re
import imaplib
import email
from email.header import decode_header

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

GMAIL_USER = "isearch.xsolve@gmail.com"
GMAIL_APP_PW = "bjpsndhhhiorkwni"

def fetch_latest_twilio_code(since_timestamp):
    print("Checking Gmail for Twilio verification code...", flush=True)
    m = imaplib.IMAP4_SSL("imap.gmail.com")
    m.login(GMAIL_USER, GMAIL_APP_PW)
    m.select("inbox")
    status, data = m.search(None, "FROM", "twilio")
    msg_ids = data[0].split()
    if not msg_ids:
        m.logout()
        return None
    
    # check latest 3 messages
    for mid in reversed(msg_ids[-3:]):
        status, msg_data = m.fetch(mid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        
        # Check date or subject
        subject, enc = decode_header(msg.get("Subject", ""))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(enc or "utf-8", errors="ignore")
            
        if "Verify your Email" in subject:
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get("Content-Disposition"))
                    if ctype == "text/plain" and "attachment" not in cdispo:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    elif ctype == "text/html" and not body:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                
            # Look for 6-char alphanumeric code after "Enter the following code to verify your email address:"
            m_code = re.search(r'Enter the following code to verify your email address:\s*([A-Z0-9]{6})', body)
            if m_code:
                code = m_code.group(1)
                m.logout()
                return code
            # General fallback
            m_gen = re.search(r'\b[A-Z0-9]{6}\b', body)
            if m_gen:
                m.logout()
                return m_gen.group(0)
    m.logout()
    return None

def main():
    EMAIL = "isearch.xsolve+backup@gmail.com"
    PASSWORD = "KiloBaba2026!#Wire"
    FIRST = "Kunal"
    LAST = "Das"
    
    start_time = time.time()
    print("=" * 60, flush=True)
    print(f"STARTING ONE-SHOT TWILIO REGISTRATION FOR {EMAIL}", flush=True)
    print("=" * 60, flush=True)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://www.twilio.com/try-twilio ...", flush=True)
        nav_res = client.navigate("https://www.twilio.com/try-twilio")
        print("Nav result:", json.dumps(nav_res, ensure_ascii=True), flush=True)
        time.sleep(6)
        
        print("[2] Filling initial signup form...", flush=True)
        fill_script = f"""
        (function() {{
            function setVal(selector, val) {{
                var el = document.querySelector(selector);
                if (!el) return 'Not found: ' + selector;
                var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(el, val);
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'Filled: ' + selector;
            }}
            
            var r1 = setVal('#first-name', '{FIRST}');
            var r2 = setVal('#last-name', '{LAST}');
            var r3 = setVal('#email', '{EMAIL}');
            var r4 = setVal('#password', '{PASSWORD}');
            
            var tos = document.querySelector('#terms-of-service');
            if (tos && !tos.checked) {{
                tos.click();
            }}
            
            return JSON.stringify({{ r1, r2, r3, r4, tos: tos ? tos.checked : false }});
        }})()
        """
        fill_res = client.call_tool("browser_execute_script", {"script": fill_script})
        print("Fill result:", json.dumps(fill_res, ensure_ascii=True), flush=True)
        time.sleep(1)
        
        client.screenshot(r"D:\anonym\twilio_reg_step1_filled.png")
        
        print("[3] Clicking Continue to submit initial form...", flush=True)
        click_script = """
        (function() {
            var btn = document.querySelector('button[name="action"]') || document.querySelector('button[type="submit"]');
            if (btn) {
                btn.click();
                return 'Clicked ' + btn.innerText;
            }
            return 'Button not found';
        })()
        """
        click_res = client.call_tool("browser_execute_script", {"script": click_script})
        print("Click result:", json.dumps(click_res, ensure_ascii=True), flush=True)
        
        print("[4] Waiting for verification screen...", flush=True)
        time.sleep(6)
        client.screenshot(r"D:\anonym\twilio_reg_step2_screen.png")
        
        # Check current screen
        check_script = """
        (function() {
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                body: document.body.innerText.slice(0, 400)
            });
        })()
        """
        screen_info = client.call_tool("browser_execute_script", {"script": check_script})
        print("Screen info:", json.dumps(screen_info, ensure_ascii=True), flush=True)
        
        print("[5] Polling Gmail for verification code...", flush=True)
        code = None
        for attempt in range(12):
            time.sleep(4)
            code = fetch_latest_twilio_code(start_time)
            if code and code != "P33XA2": # Ensure it's not the older code
                print(f"==> NEW VERIFICATION CODE FOUND: {code}", flush=True)
                break
            else:
                print(f"Waiting for new code (attempt {attempt+1}/12)...", flush=True)
                
        if not code or code == "P33XA2":
            print("ERROR: Did not receive new verification code in time!", flush=True)
            return
            
        print(f"[6] Filling verification code {code} into screen...", flush=True)
        fill_code_script = f"""
        (function() {{
            var input = document.querySelector('input[type="text"]') || document.querySelector('input');
            if (!input) return 'Input not found';
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(input, '{code}');
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Code filled successfully: ' + (input.id || input.name || 'input');
        }})()
        """
        code_res = client.call_tool("browser_execute_script", {"script": fill_code_script})
        print("Fill code result:", json.dumps(code_res, ensure_ascii=True), flush=True)
        time.sleep(1)
        client.screenshot(r"D:\anonym\twilio_reg_step3_code_filled.png")
        
        print("[7] Submitting verification code...", flush=True)
        submit_code_script = """
        (function() {
            var btn = document.querySelector('button[type="submit"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Continue'));
            if (btn) {
                btn.click();
                return 'Clicked button: ' + btn.innerText;
            }
            return 'Button not found';
        })()
        """
        sub_res = client.call_tool("browser_execute_script", {"script": submit_code_script})
        print("Submit code result:", json.dumps(sub_res, ensure_ascii=True), flush=True)
        
        print("[8] Waiting for Phone / 2FA screen...", flush=True)
        time.sleep(7)
        client.screenshot(r"D:\anonym\twilio_reg_step4_phone_screen.png")
        
        final_info = client.call_tool("browser_execute_script", {"script": check_script})
        print("Final step screen info:", json.dumps(final_info, ensure_ascii=True), flush=True)
        
    except Exception as e:
        print("Error during registration:", repr(e), flush=True)
    finally:
        client.close()
        print("Agent360 client closed.", flush=True)

if __name__ == "__main__":
    main()
